// E7 Bridge v0.8.3: native Qt 4.7.4 agent for Nokia Belle.
// Manually launched, outbound TCP, HMAC authenticated.
// Host may send signed admin writes to public data storage / package staging.
// No raw shell, boot service, or firmware modification commands.
#include <QtGui/QApplication>
#include <QtGui/QWidget>
#include <QtGui/QLabel>
#include <QtGui/QLineEdit>
#include <QtGui/QPushButton>
#include <QtGui/QCheckBox>
#include <QtGui/QDesktopServices>
#include <QtGui/QVBoxLayout>
#include <QtGui/QHBoxLayout>
#include <QtGui/QFormLayout>
#include <QtNetwork/QTcpSocket>
#include <QtNetwork/QHostAddress>
#include <QtNetwork/QNetworkSession>
#include <QtNetwork/QNetworkConfigurationManager>
#include "sha256_compat.h"
#include <QtCore/QDir>
#include <QtCore/QFileInfo>
#include <QtCore/QFile>
#include <QtCore/QUrl>
#include <QtCore/QByteArray>
#include <QtCore/QSettings>
#include <QtCore/QRegExp>
#include <QtCore/QStringList>
#ifdef Q_OS_SYMBIAN
#include <QtGui/QSymbianEvent> // Qt 4.7 native event wrapper
#include <w32std.h> // TWsEvent from the Symbian Window Server
#include <coemain.h> // CCoeEnv::RootWin() gives our native window group
#include <e32base.h> // Symbian native types, including TUint32
// TFindProcess and TFullName enumerate process names read-only.
#include <e32property.h> // RProperty::Get; read only
#include <hal.h> // HAL::Get; read only
// Symbian^3 public avkon.hrh: KAknUidValueEndKeyCloseEvent = 0x101F87F0.
// Do not include the entire resource header: the pinned Belle SDK copy pulls
// in AknFontCategory.hrh, unavailable in the compiler include paths.
static const TUint32 KE7EndKeyCloseEvent = 0x101F87F0u;
#include <swi/sisregistrysession.h> // InstalledUidsL/IsInstalledL: ReadUserData
#include <swi/sisregistryentry.h> // PackageNameL/VersionL: read-only
#endif

static const int kPort = 46270;
static const int kMaxLine = 4096;
// The v0.5 read-only transfer pilot is deliberately limited to ONE known,
// previously deployed synthetic fixture. No user-selected path or remote write.
static const char kProbePath[] = "E:/KAI/INDEX.HTM";
static const qint64 kProbeLimit = 65536;
static const qint64 kProbeChunk = 1024;
static const qint64 kAdminChunk = 2048;
static const qint64 kAdminMaxBytes = 8388608; // 8 MiB per transfer, streamed.


// HMAC-SHA256 must match the Debian Python hmac module exactly.
// Qt 4.7.4 lacks a SHA-256 hash enum, so use the small portable
// SHA-256 implementation in sha256_compat.h instead of weakening the protocol.
static QByteArray hmac256(const QByteArray &secret, const QByteArray &message) {
    unsigned char digest[32];
    e7_hmac_sha256(
        reinterpret_cast<const unsigned char *>(secret.constData()),
        static_cast<unsigned int>(secret.size()),
        reinterpret_cast<const unsigned char *>(message.constData()),
        static_cast<unsigned int>(message.size()), digest);
    return QByteArray(reinterpret_cast<const char *>(digest), 32).toHex();
}

// Safety boundary for both LIST and STAT: E: and C:/Data only.
// Re-check canonical paths too, so a filesystem alias cannot bypass the rules.
static bool allowedPath(const QString &candidate) {
    const QString lower = QDir::cleanPath(candidate).toLower();
    if (!(lower == "e:/" || lower.startsWith("e:/") ||
          lower == "c:/data" || lower.startsWith("c:/data/")))
        return false;
    const QStringList segments = lower.split('/', QString::SkipEmptyParts);
    return !segments.contains("private") && !segments.contains("sys") &&
           !segments.contains("resource");
}

static bool resolvedPath(const QString &requested, QString *resolved) {
    if (requested.contains('\n') || requested.contains('\r')) return false;
    const QString clean = QDir::cleanPath(QString(requested).replace('\\', '/'));
    if (!allowedPath(clean)) return false;
    const QString canonical = QFileInfo(clean).canonicalFilePath();
    if (canonical.isEmpty() || !allowedPath(canonical)) return false;
    *resolved = canonical;
    return true;
}

// The red End key is a native AVKON close message, NOT a normal Qt keypress.
// By default it exits a Qt GUI. Intercept only while our owner explicitly
// connected and authenticated this session; never create a boot daemon.
class E7BridgeApplication : public QApplication {
public:
    E7BridgeApplication(int &argc, char **argv)
        : QApplication(argc, argv), preserveConnectedSession(false) {}

    void setPreserveConnectedSession(bool enabled) {
        preserveConnectedSession = enabled;
    }

#ifdef Q_OS_SYMBIAN
protected:
    virtual bool symbianEventFilter(const QSymbianEvent *event) {
        if (preserveConnectedSession && event &&
            event->type() == QSymbianEvent::WindowServerEvent &&
            event->windowServerEvent() &&
            event->windowServerEvent()->Type() == KE7EndKeyCloseEvent) {
            // Symbian still foregrounds its native Phone UI. Do not close
            // the Qt event loop, TCP socket, or running bridge process.
            return true;
        }
        return QApplication::symbianEventFilter(event);
    }
#endif
private:
    bool preserveConnectedSession;
};

class E7Bridge : public QWidget {
    Q_OBJECT
public:
    E7Bridge(E7BridgeApplication *app, QWidget *parent = 0)
        : QWidget(parent), bridgeApp(app), socket(new QTcpSocket(this)), session(0),
          authenticated(false), awaitingReady(false), wantConnection(false),
          adminSequence(0), uploadActive(false), uploadSize(0), uploadReceived(0) {
        setWindowTitle("E7 Bridge");
        QLabel *intro = new QLabel(
            "E7 Bridge v0.8.3\nAuthenticated diagnostic + admin link", this);
        intro->setWordWrap(true);
        server = new QLineEdit(this);
        server->setInputMethodHints(Qt::ImhNoPredictiveText);
        key = new QLineEdit(this);
        key->setInputMethodHints(Qt::ImhNoPredictiveText);
        key->setMaxLength(16);
        key->setEchoMode(QLineEdit::Password);
        QFormLayout *form = new QFormLayout();
        form->addRow("Debian IPv4", server);
        form->addRow("Pairing key", key);
        remember = new QCheckBox("Remember IP + key on this phone", this);
        remember->setChecked(true);
        QPushButton *forgetButton = new QPushButton("Forget saved pairing", this);
        QPushButton *connectButton = new QPushButton("Connect", this);
        QPushButton *disconnectButton = new QPushButton("Disconnect", this);
        QPushButton *backgroundButton = new QPushButton("Background", this);
        QPushButton *exitButton = new QPushButton("Exit Bridge", this);
        state = new QLabel("Idle. Connect manually; no background link yet.", this);
        state->setWordWrap(true);
        QVBoxLayout *layout = new QVBoxLayout(this);
        layout->addWidget(intro);
        layout->addLayout(form);
        layout->addWidget(remember);
        layout->addWidget(forgetButton);
        layout->addWidget(connectButton);
        layout->addWidget(disconnectButton);
        QHBoxLayout *backgroundActions = new QHBoxLayout();
        backgroundActions->addWidget(backgroundButton);
        backgroundActions->addWidget(exitButton);
        layout->addLayout(backgroundActions);
        layout->addWidget(state);
        connect(connectButton, SIGNAL(clicked()), this, SLOT(startLink()));
        connect(disconnectButton, SIGNAL(clicked()), this, SLOT(stopLink()));
        connect(backgroundButton, SIGNAL(clicked()), this, SLOT(backgroundNow()));
        connect(exitButton, SIGNAL(clicked()), this, SLOT(exitBridge()));
        connect(forgetButton, SIGNAL(clicked()), this, SLOT(forgetPairing()));
        connect(remember, SIGNAL(toggled(bool)), this, SLOT(onRememberToggled(bool)));
        connect(socket, SIGNAL(connected()), this, SLOT(onConnected()));
        connect(socket, SIGNAL(disconnected()), this, SLOT(onDisconnected()));
        connect(socket, SIGNAL(readyRead()), this, SLOT(onData()));
        connect(socket, SIGNAL(error(QAbstractSocket::SocketError)),
                this, SLOT(onSocketError(QAbstractSocket::SocketError)));
        restoreSavedPairing(); // Prefill only; NEVER initiate networking at startup.
    }
private slots:
    void backgroundNow() {
        if (!authenticated || socket->state() != QAbstractSocket::ConnectedState) {
            state->setText("Connect and authenticate before backgrounding.");
            return;
        }
        // Qt 4.7 showMinimized() can leave a Belle window un-restorable
        // from the native task switcher. On Symbian, send the application
        // window group behind other apps without setting Qt::WindowMinimized.
        // Keep the QWidget, event loop and authenticated socket alive.
#ifdef Q_OS_SYMBIAN
        CCoeEnv *coe = CCoeEnv::Static();
        if (!coe) {
            state->setText("Cannot background: Symbian UI environment unavailable.");
            return;
        }
        state->setText("Connected in background. Hold Menu and select E7 Bridge to return.");
        coe->RootWin().SetOrdinalPosition(-1);
#else
        state->setText("Connected in background. Return via task switcher; Exit to stop.");
        showMinimized();
#endif
    }
    void exitBridge() {
        // Deliberate owner exit, unlike a focus change or Symbian End key.
        stopLink();
        QApplication::quit();
    }
    void onRememberToggled(bool enabled) {
        if (enabled) return; // Re-enable saving only after the next successful handshake.
        if (clearSavedPairing())
            state->setText("Remember disabled; saved pairing cleared.");
        else
            state->setText("Cannot clear saved pairing; check phone storage.");
    }
    void forgetPairing() {
        stopLink();
        remember->blockSignals(true);
        remember->setChecked(false);
        remember->blockSignals(false);
        const bool erased = clearSavedPairing();
        server->clear();
        key->clear();
        state->setText(erased ? "Saved pairing forgotten; no auto-connect."
                              : "Could not erase saved pairing; inspect C: storage.");
    }
    void startLink() {
        if (socket->state() != QAbstractSocket::UnconnectedState) {
            state->setText("Already connecting or connected.");
            return;
        }
        const QHostAddress addr(server->text().trimmed());
        if (addr.isNull() || addr.protocol() != QAbstractSocket::IPv4Protocol) {
            state->setText("Enter Debian's numeric IPv4 address.");
            return;
        }
        if (!QRegExp("[0-9a-f]{16}").exactMatch(key->text().trimmed().toLower())) {
            state->setText("Pairing key must contain 16 hexadecimal characters.");
            return;
        }
        authenticated = false;
        awaitingReady = false;
        adminSequence = 0;
        abortUpload();
        wantConnection = true;
        // Freeze validated input until the handshake completes or fails.
        server->setEnabled(false);
        key->setEnabled(false);
        incoming.clear();
        state->setText("Opening Wi-Fi bearer...");
        QNetworkConfigurationManager manager;
        const QNetworkConfiguration config = manager.defaultConfiguration();
        if (config.isValid() &&
            (manager.capabilities() & QNetworkConfigurationManager::NetworkSessionRequired)) {
            if (session) {
                session->close();
                session->deleteLater();
                session = 0;
            }
            session = new QNetworkSession(config, this);
            connect(session, SIGNAL(opened()), this, SLOT(openSocket()));
            connect(session, SIGNAL(error(QNetworkSession::SessionError)),
                    this, SLOT(onSessionError(QNetworkSession::SessionError)));
            session->open();
        } else {
            openSocket();
        }
    }
    void openSocket() {
        if (!wantConnection) return;
        if (socket->state() != QAbstractSocket::UnconnectedState) return;
        state->setText("Connecting to Debian; keep Wi-Fi connected...");
        socket->connectToHost(server->text().trimmed(), kPort);
    }
    void stopLink() {
        abortUpload();
        adminSequence = 0;
        wantConnection = false;
        bridgeApp->setPreserveConnectedSession(false);
        socket->abort();
        authenticated = false;
        awaitingReady = false;
        incoming.clear();
        server->setEnabled(true);
        key->setEnabled(true);
        if (session) {
            session->close();
            session->deleteLater();
            session = 0;
        }
        state->setText("Stopped. No background service remains.");
    }
    void onConnected() { state->setText("Connected; authenticating..."); }
    void onDisconnected() {
        abortUpload();
        adminSequence = 0;
        wantConnection = false;
        bridgeApp->setPreserveConnectedSession(false);
        authenticated = false;
        awaitingReady = false;
        incoming.clear();
        server->setEnabled(true);
        key->setEnabled(true);
        state->setText("Disconnected. Reconnect manually when ready.");
    }
    void onSocketError(QAbstractSocket::SocketError) {
        abortUpload();
        wantConnection = false;
        bridgeApp->setPreserveConnectedSession(false);
        server->setEnabled(true);
        key->setEnabled(true);
        state->setText("Network error: " + socket->errorString());
    }
    void onSessionError(QNetworkSession::SessionError) {
        abortUpload();
        wantConnection = false;
        bridgeApp->setPreserveConnectedSession(false);
        server->setEnabled(true);
        key->setEnabled(true);
        state->setText("Wi-Fi session failed; connect Wi-Fi in Settings first.");
    }
    void onData() {
        incoming.append(socket->readAll());
        // Bound each frame, NOT the accumulated TCP read. Multiple legitimate
        // protocol lines may arrive in a single readReady() callback.
        for (;;) {
            const int boundary = incoming.indexOf('\n');
            if (boundary < 0) {
                if (incoming.size() > kMaxLine) rejectOversize();
                return;
            }
            if (boundary > kMaxLine) { rejectOversize(); return; }
            const QByteArray line = incoming.left(boundary).trimmed();
            incoming.remove(0, boundary + 1);
            handleLine(line);
            if (socket->state() != QAbstractSocket::ConnectedState) return;
        }
    }
    void rejectOversize() {
        state->setText("Oversized protocol line rejected.");
        socket->abort();
    }
    void sendLine(const QByteArray &message) {
        if (socket->state() == QAbstractSocket::ConnectedState &&
            message.size() <= kMaxLine - 2 &&
            !message.contains('\n') && !message.contains('\r'))
            socket->write(message + "\n");
    }
    void handleLine(const QByteArray &line) {
        if (awaitingReady) {
            const QByteArray expected = "E7B1 READY " +
                hmac256(key->text().trimmed().toLower().toLatin1(),
                        "host:" + challengeNonce);
            if (line != expected) {
                state->setText("Host authentication failed.");
                socket->abort();
                return;
            }
            authenticated = true;
            bridgeApp->setPreserveConnectedSession(true);
            adminSequence = 0;
            awaitingReady = false;
            key->setEnabled(false);
            if (remember->isChecked()) {
                // Persist only AFTER validating the host's READY HMAC above.
                // Symbian applicationDirPath() is our UID3-caged private folder.
                // This file is not encrypted; use a trusted device and LAN.
                const bool saved = savePairing();
                state->setText(saved ?
                    "Authenticated; pairing remembered (private local settings)." :
                    "Authenticated; could not save pairing. Check C: storage.");
            } else {
                state->setText("Authenticated; pairing not saved.");
            }
            state->setText(state->text() +
                " Use Background/End key; task switcher to return; Exit to stop.");
            return;
        }
        if (!authenticated) {
            if (!line.startsWith("E7B1 CHALLENGE ")) {
                socket->abort();
                return;
            }
            const QByteArray nonce = line.mid(15);
            if (!QRegExp("[0-9a-f]{32}").exactMatch(QString::fromLatin1(nonce))) {
                socket->abort();
                return;
            }
            challengeNonce = nonce;
            sendLine("E7B1 AUTH " +
                     hmac256(key->text().trimmed().toLower().toLatin1(),
                             "device:" + nonce));
            awaitingReady = true;
            key->setEnabled(false);
            return;
        }
        if (line.startsWith("ADM ")) { handleAdminLine(line); return; }
        if (line == "PING") { sendLine("OK PONG"); return; }
        if (line == "INFO") {
            sendLine("OK Nokia Belle; Qt " + QByteArray(QT_VERSION_STR) +
                     "; E7 Bridge v0.8.3");
            return;
        }
        if (line == "METRICS") { sendMetrics(); return; }
        if (line.startsWith("PKGS ")) {
            const QByteArray arg = line.mid(5);
            if (!QRegExp("[0-9]{1,4}").exactMatch(QString::fromLatin1(arg))) {
                sendLine("ERR BAD_PACKAGE_OFFSET"); return;
            }
            bool ok = false;
            const int offset = arg.toInt(&ok);
            if (!ok || offset > 2000) { sendLine("ERR BAD_PACKAGE_OFFSET"); return; }
            listInstalledPackages(offset);
            return;
        }
        if (line.startsWith("PKG ")) {
            const QByteArray arg = line.mid(4);
            if (!QRegExp("[0-9a-fA-F]{8}").exactMatch(QString::fromLatin1(arg))) {
                sendLine("ERR BAD_PACKAGE_UID"); return;
            }
            bool ok = false;
            const uint uid = arg.toUInt(&ok, 16);
            if (!ok) { sendLine("ERR BAD_PACKAGE_UID"); return; }
            queryInstalledPackage(TUid::Uid(static_cast<TInt>(uid)));
            return;
        }
        if (line == "FILEINFO") { sendProbeInfo(); return; }
        if (line.startsWith("FILECHUNK ")) {
            const QByteArray arg = line.mid(10);
            if (!QRegExp("[0-9]{1,5}").exactMatch(QString::fromLatin1(arg))) {
                sendLine("ERR BAD_OFFSET"); return;
            }
            bool ok = false;
            const qint64 offset = arg.toLongLong(&ok);
            if (!ok || offset < 0 || offset >= kProbeLimit ||
                (offset % kProbeChunk) != 0) {
                sendLine("ERR BAD_OFFSET"); return;
            }
            sendProbeChunk(offset);
            return;
        }
        if (line.startsWith("PROCS ")) {
            const QByteArray arg = line.mid(6);
            if (!QRegExp("[0-9]{1,4}").exactMatch(QString::fromLatin1(arg))) {
                sendLine("ERR BAD_OFFSET"); return;
            }
            bool ok = false;
            const int offset = arg.toInt(&ok);
            if (!ok || offset > 2000) { sendLine("ERR BAD_OFFSET"); return; }
            listProcesses(offset);
            return;
        }
        if (line == "DRIVES") {
            QStringList output;
            if (QDir("E:/").exists()) output << "[D] E:/";
            if (QDir("C:/Data").exists()) output << "[D] C:/Data";
            sendB64(output.join("\n"));
            return;
        }
        if (line.startsWith("LIST ")) {
            listDir(QString::fromUtf8(line.mid(5)));
            return;
        }
        if (line.startsWith("STAT ")) {
            statPath(QString::fromUtf8(line.mid(5)));
            return;
        }
        if (line == "QUIT") {
            sendLine("OK BYE");
            socket->disconnectFromHost();
            return;
        }
        sendLine("ERR UNKNOWN_COMMAND");
    }
    // Administrative packets are MACed separately from the handshake:
    // HMAC(key, "admin:" + nonce + ":" + seq + ":" + verb + args).
    // Replies are also MACed and bind the same nonce/sequence. No replay
    // within the current authenticated connection. The channel is NOT encrypted.
    static bool equalMac(const QByteArray &a, const QByteArray &b) {
        if (a.size() != 64 || b.size() != 64) return false;
        unsigned char mismatch = 0;
        for (int i = 0; i < 64; ++i)
            mismatch |= static_cast<unsigned char>(a.at(i) ^ b.at(i));
        return mismatch == 0;
    }
    void adminReply(int seq, const QByteArray &body) {
        const QByteArray number = QByteArray::number(seq);
        const QByteArray mac = hmac256(key->text().trimmed().toLower().toLatin1(),
            "reply:" + challengeNonce + ":" + number + ":" + body);
        sendLine("ADMREPLY " + number + " " + body + " " + mac);
    }
    void handleAdminLine(const QByteArray &line) {
        const int first = line.indexOf(' ', 4);
        const int last = line.lastIndexOf(' ');
        if (first < 5 || last <= first + 1) {
            sendLine("ERR ADMIN_FORMAT"); return;
        }
        const QByteArray seqBytes = line.mid(4, first - 4);
        if (!QRegExp("[1-9][0-9]{0,7}").exactMatch(QString::fromLatin1(seqBytes))) {
            sendLine("ERR ADMIN_SEQUENCE"); return;
        }
        bool ok = false;
        const int seq = seqBytes.toInt(&ok);
        if (!ok || seq != adminSequence + 1) {
            sendLine("ERR ADMIN_SEQUENCE"); return;
        }
        const QByteArray command = line.mid(first + 1, last - first - 1);
        const QByteArray remoteMac = line.mid(last + 1);
        if (command.size() > kMaxLine - 100 || command.isEmpty()) {
            sendLine("ERR ADMIN_FORMAT"); return;
        }
        const QByteArray expected = hmac256(
            key->text().trimmed().toLower().toLatin1(),
            "admin:" + challengeNonce + ":" + seqBytes + ":" + command);
        if (!equalMac(remoteMac, expected)) {
            sendLine("ERR ADMIN_AUTH"); return;
        }
        adminSequence = seq;
        const QList<QByteArray> items = command.split(' ');
        if (items.size() == 5 && items[0] == "BEGIN") {
            beginUpload(seq, items);
        } else if (items.size() == 3 && items[0] == "CHUNK") {
            uploadChunk(seq, items);
        } else if (items.size() == 1 && items[0] == "FINISH") {
            finishUpload(seq);
        } else if (items.size() == 4 && items[0] == "LAUNCH") {
            launchInstaller(seq, items);
        } else if (items.size() == 1 && items[0] == "CANCEL") {
            abortUpload();
            adminReply(seq, "OK CANCELLED");
        } else {
            adminReply(seq, "ERR ADMIN_UNKNOWN");
        }
    }
    void abortUpload() {
        if (uploadFile.isOpen()) uploadFile.close();
        if (!uploadTemp.isEmpty()) QFile::remove(uploadTemp);
        uploadTemp.clear();
        uploadTarget.clear();
        uploadExpected.clear();
        uploadSize = 0;
        uploadReceived = 0;
        uploadActive = false;
    }
    void beginUpload(int seq, const QList<QByteArray> &items) {
        if (uploadActive) { adminReply(seq, "ERR UPLOAD_BUSY"); return; }
        const QByteArray bucket = items[1];
        const QString name = QString::fromLatin1(items[2].constData());
        const QByteArray sizeString = items[3];
        const QByteArray hash = items[4];
        if (!QRegExp("[A-Za-z0-9][A-Za-z0-9._-]{0,63}").exactMatch(name) ||
            name.contains("..") || name.endsWith(".")) {
            adminReply(seq, "ERR NAME_REJECTED"); return;
        }
        if ((bucket != "inbox" && bucket != "installs") ||
            (bucket == "installs" &&
             !(name.endsWith(".sis", Qt::CaseInsensitive) ||
               name.endsWith(".sisx", Qt::CaseInsensitive)))) {
            adminReply(seq, "ERR DESTINATION_REJECTED"); return;
        }
        if (!QRegExp("[0-9]{1,8}").exactMatch(QString::fromLatin1(sizeString)) ||
            !QRegExp("[0-9a-f]{64}").exactMatch(QString::fromLatin1(hash))) {
            adminReply(seq, "ERR MANIFEST_REJECTED"); return;
        }
        bool sizeOkay = false;
        const qint64 size = sizeString.toLongLong(&sizeOkay);
        if (!sizeOkay || size > kAdminMaxBytes) {
            adminReply(seq, "ERR TOO_LARGE"); return;
        }
        const QString parent = bucket == "installs" ? "E:/Installs" : "E:/KAI/INBOX";
        // Canonical check catches redirected/Symbian symlinked destination dirs.
        // E: is deliberately user storage, not sys/bin or ROM Z:.
        // Inspect existing ancestors BEFORE creating any directory.
        // A redirected E:/KAI parent must never cause us to create elsewhere.
        if (QDir("E:/").canonicalPath().compare("E:/", Qt::CaseInsensitive) != 0 ||
            (bucket == "inbox" && QDir("E:/KAI").exists() &&
             QDir("E:/KAI").canonicalPath().compare("E:/KAI", Qt::CaseInsensitive) != 0)) {
            adminReply(seq, "ERR STORAGE_REDIRECTED"); return;
        }
        if (!QDir().mkpath(parent) ||
            QDir(parent).canonicalPath().compare(parent, Qt::CaseInsensitive) != 0 ||
            QFileInfo(parent).isSymLink()) {
            adminReply(seq, "ERR STORAGE_UNAVAILABLE"); return;
        }
        const QString finalName = parent + "/" + name;
        if (QFileInfo(finalName).exists() || QFileInfo(finalName).isSymLink()) {
            adminReply(seq, "ERR EXISTS"); return;
        }
        const QString temp = parent + "/.e7bridge-" + QString::fromLatin1(challengeNonce) + ".part";
        if (QFileInfo(temp).exists() || QFileInfo(temp).isSymLink()) {
            adminReply(seq, "ERR STALE_STAGE"); return;
        }
        uploadFile.setFileName(temp);
        if (!uploadFile.open(QIODevice::WriteOnly)) {
            adminReply(seq, "ERR CANNOT_CREATE_STAGE"); return;
        }
        uploadTemp = temp;
        uploadTarget = finalName;
        uploadExpected = hash;
        uploadSize = size;
        uploadReceived = 0;
        uploadActive = true;
        e7_sha256_init(&uploadHash);
        adminReply(seq, "OK READY");
    }
    void uploadChunk(int seq, const QList<QByteArray> &items) {
        if (!uploadActive) { adminReply(seq, "ERR NO_UPLOAD"); return; }
        const QByteArray offsetString = items[1];
        if (!QRegExp("[0-9]{1,8}").exactMatch(QString::fromLatin1(offsetString))) {
            adminReply(seq, "ERR OFFSET_INVALID"); return;
        }
        bool ok = false;
        const qint64 offset = offsetString.toLongLong(&ok);
        if (!ok || offset != uploadReceived) {
            adminReply(seq, "ERR OFFSET_MISMATCH"); return;
        }
        const QByteArray encoded = items[2];
        const QByteArray block = QByteArray::fromBase64(encoded);
        if (block.isEmpty() || block.size() > kAdminChunk ||
            block.toBase64() != encoded || uploadReceived + block.size() > uploadSize) {
            adminReply(seq, "ERR CHUNK_INVALID"); return;
        }
        const qint64 written = uploadFile.write(block);
        if (written != block.size()) {
            abortUpload();
            adminReply(seq, "ERR WRITE_FAILED"); return;
        }
        e7_sha256_update(&uploadHash,
            reinterpret_cast<const unsigned char *>(block.constData()),
            static_cast<unsigned int>(block.size()));
        uploadReceived += block.size();
        adminReply(seq, "OK CHUNK");
    }
    void finishUpload(int seq) {
        if (!uploadActive) { adminReply(seq, "ERR NO_UPLOAD"); return; }
        if (uploadReceived != uploadSize) {
            adminReply(seq, "ERR INCOMPLETE"); return;
        }
        if (!uploadFile.flush()) {
            abortUpload(); adminReply(seq, "ERR FLUSH_FAILED"); return;
        }
        uploadFile.close();
        unsigned char digest[32];
        e7_sha256_final(&uploadHash, digest);
        const QByteArray computed = QByteArray(
            reinterpret_cast<const char *>(digest), 32).toHex();
        if (computed != uploadExpected) {
            abortUpload(); adminReply(seq, "ERR HASH_MISMATCH"); return;
        }
        if (QFileInfo(uploadTarget).exists() ||
            !QFile::rename(uploadTemp, uploadTarget)) {
            abortUpload(); adminReply(seq, "ERR PUBLISH_FAILED"); return;
        }
        const QByteArray result = "OK STORED " + QByteArray::number(uploadSize) +
                                  " " + computed;
        // Publish succeeded. Do not remove the newly renamed destination.
        uploadTemp.clear();
        uploadTarget.clear();
        uploadExpected.clear();
        uploadSize = 0;
        uploadReceived = 0;
        uploadActive = false;
        adminReply(seq, result);
    }

    // An owner-authenticated LAUNCH can open only a previously staged .sis/.sisx
    // package from E:/Installs. The host includes its known size and digest;
    // independently recompute both on-device before handing it to AppArc.
    // A successful openUrl is only an installer-launch request, NOT evidence
    // of installation. Platform UI/signing policy still applies.
    void launchInstaller(int seq, const QList<QByteArray> &items) {
        if (uploadActive) { adminReply(seq, "ERR UPLOAD_BUSY"); return; }
        const QString name = QString::fromLatin1(items[1].constData());
        if (!QRegExp("[A-Za-z0-9][A-Za-z0-9._-]{0,63}").exactMatch(name) ||
            name.contains("..") || name.endsWith(".") ||
            !(name.endsWith(".sis", Qt::CaseInsensitive) ||
              name.endsWith(".sisx", Qt::CaseInsensitive))) {
            adminReply(seq, "ERR PACKAGE_NAME"); return;
        }
        if (!QRegExp("[0-9]{1,8}").exactMatch(QString::fromLatin1(items[2])) ||
            !QRegExp("[0-9a-f]{64}").exactMatch(QString::fromLatin1(items[3]))) {
            adminReply(seq, "ERR PACKAGE_MANIFEST"); return;
        }
        bool sizeOkay = false;
        const qint64 expectedSize = items[2].toLongLong(&sizeOkay);
        if (!sizeOkay || expectedSize < 1 || expectedSize > kAdminMaxBytes) {
            adminReply(seq, "ERR PACKAGE_SIZE"); return;
        }
        const QString parent = "E:/Installs";
        const QDir installDir(parent);
        if (!installDir.exists() ||
            installDir.canonicalPath().compare(parent, Qt::CaseInsensitive) != 0 ||
            QFileInfo(parent).isSymLink()) {
            adminReply(seq, "ERR INSTALL_DIRECTORY"); return;
        }
        const QString path = parent + "/" + name;
        const QFileInfo info(path);
        if (!info.exists() || !info.isFile() || info.isSymLink() ||
            info.size() != expectedSize ||
            info.canonicalFilePath().compare(path, Qt::CaseInsensitive) != 0) {
            adminReply(seq, "ERR PACKAGE_MISSING_OR_CHANGED"); return;
        }
        QFile staged(path);
        if (!staged.open(QIODevice::ReadOnly)) {
            adminReply(seq, "ERR PACKAGE_UNREADABLE"); return;
        }
        E7Sha256State hash;
        e7_sha256_init(&hash);
        qint64 seen = 0;
        for (;;) {
            const QByteArray bytes = staged.read(16384);
            if (bytes.isEmpty()) break;
            seen += bytes.size();
            if (seen > expectedSize) {
                staged.close();
                adminReply(seq, "ERR PACKAGE_CHANGED"); return;
            }
            e7_sha256_update(&hash,
                reinterpret_cast<const unsigned char *>(bytes.constData()),
                static_cast<unsigned int>(bytes.size()));
        }
        const bool readOkay = (staged.error() == QFile::NoError);
        staged.close();
        unsigned char digest[32];
        e7_sha256_final(&hash, digest);
        const QByteArray actual = QByteArray(
            reinterpret_cast<const char *>(digest), 32).toHex();
        if (!readOkay || seen != expectedSize || actual != items[3]) {
            adminReply(seq, "ERR PACKAGE_HASH_MISMATCH"); return;
        }
        // Qt 4.7 on Symbian delegates file URLs to the registered native
        // handler. It may show installer prompts; we do not bypass SWI policy.
        const bool requested = QDesktopServices::openUrl(QUrl::fromLocalFile(path));
        if (!requested) {
            adminReply(seq, "ERR INSTALLER_OPEN_FAILED");
            state->setText("Unable to open staged SIS installer.");
            return;
        }
        adminReply(seq, "OK LAUNCH_REQUESTED");
        state->setText("Installer launch requested for " + name +
                       ". Complete/inspect Belle installer if prompted.");
    }

    // v0.8: query the native Software Install registry, not AppArc menu icons.
    // A data-only package has no launcher registration but does have a SIS UID.
    // RSisRegistrySession::InstalledUidsL requires ReadUserData, already held.
    // Use small, deterministic pages and never expose package-owned file paths.
    static QString registryUid(TUid uid) {
        return "0x" + QString("%1").arg(static_cast<uint>(uid.iUid),
                                         8, 16, QChar('0')).toUpper();
    }
    static QString registryName(const HBufC *name) {
        if (!name) return "(unnamed)";
        const QString raw = QString::fromUtf16(
            reinterpret_cast<const ushort *>(name->Ptr()), name->Length());
        QString result;
        for (int i = 0; i < raw.size() && result.size() < 100; ++i) {
            const ushort c = raw.at(i).unicode();
            result.append(c >= 32 && c <= 126 && c != '|' ? QChar(c) : QChar('?'));
        }
        return result.isEmpty() ? "(unnamed)" : result;
    }
    static QString registryVersion(const TVersion &value) {
        return QString::number(value.iMajor) + "." +
               QString::number(value.iMinor) + "." +
               QString::number(value.iBuild);
    }
    void queryInstalledPackage(TUid uid) {
#ifdef Q_OS_SYMBIAN
        Swi::RSisRegistrySession registry;
        const TInt sessionError = registry.Connect();
        if (sessionError != KErrNone) {
            sendLine("ERR REGISTRY_CONNECT " + QByteArray::number(sessionError));
            return;
        }
        Swi::RSisRegistryEntry entry;
        const TInt openError = entry.Open(registry, uid);
        if (openError == KErrNotFound) {
            registry.Close();
            sendB64("uid=" + registryUid(uid) + "\ninstalled=no");
            return;
        }
        if (openError != KErrNone) {
            registry.Close();
            sendLine("ERR REGISTRY_OPEN " + QByteArray::number(openError));
            return;
        }
        TVersion version(0, 0, 0);
        TRAPD(versionError, version = entry.VersionL());
        HBufC *name = 0;
        TRAPD(nameError, name = entry.PackageNameL());
        const QString label = registryName(name);
        delete name;
        entry.Close();
        registry.Close();
        if (versionError != KErrNone || nameError != KErrNone) {
            sendLine("ERR REGISTRY_READ"); return;
        }
        sendB64("uid=" + registryUid(uid) +
                "\ninstalled=yes\nversion=" + registryVersion(version) +
                "\nname=" + label);
#else
        Q_UNUSED(uid);
        sendLine("ERR SYMBIAN_ONLY");
#endif
    }
    void listInstalledPackages(int offset) {
#ifdef Q_OS_SYMBIAN
        Swi::RSisRegistrySession registry;
        const TInt sessionError = registry.Connect();
        if (sessionError != KErrNone) {
            sendLine("ERR REGISTRY_CONNECT " + QByteArray::number(sessionError));
            return;
        }
        RArray<TUid> uids;
        TRAPD(listError, registry.InstalledUidsL(uids));
        if (listError != KErrNone || uids.Count() > 2000) {
            uids.Close(); registry.Close();
            sendLine("ERR REGISTRY_LIST_FAILED"); return;
        }
        // The OS does not promise list order; sort UID values for stable paging.
        for (int i = 0; i < uids.Count(); ++i) {
            for (int j = i + 1; j < uids.Count(); ++j) {
                if (static_cast<uint>(uids[j].iUid) < static_cast<uint>(uids[i].iUid)) {
                    const TUid tmp = uids[i]; uids[i] = uids[j]; uids[j] = tmp;
                }
            }
        }
        QStringList lines;
        lines << "total=" + QString::number(uids.Count());
        const int end = qMin(offset + 12, uids.Count());
        for (int i = offset; i < end; ++i) {
            Swi::RSisRegistryEntry entry;
            if (entry.Open(registry, uids[i]) != KErrNone) {
                uids.Close(); registry.Close();
                sendLine("ERR REGISTRY_ENTRY_OPEN"); return;
            }
            TVersion version(0, 0, 0);
            TRAPD(versionError, version = entry.VersionL());
            HBufC *name = 0;
            TRAPD(nameError, name = entry.PackageNameL());
            const QString label = registryName(name);
            delete name;
            entry.Close();
            if (versionError != KErrNone || nameError != KErrNone) {
                uids.Close(); registry.Close();
                sendLine("ERR REGISTRY_ENTRY_READ"); return;
            }
            lines << registryUid(uids[i]) + "|" + registryVersion(version) + "|" + label;
        }
        if (end < uids.Count()) lines << "[NEXT] " + QString::number(end);
        else lines << "[END]";
        uids.Close();
        registry.Close();
        sendB64(lines.join("\n"));
#else
        Q_UNUSED(offset);
        sendLine("ERR SYMBIAN_ONLY");
#endif
    }
    void listProcesses(int offset) {
#ifdef Q_OS_SYMBIAN
        // TFindProcess returns names only. We do not open, kill, or control a process.
        // Fixed-size pages avoid exceeding the 4096-byte TCP envelope.
        TFindProcess finder;
        TFullName name;
        QStringList result;
        int index = 0;
        int emitted = 0;
        bool hasMore = false;
        while (finder.Next(name) == KErrNone) {
            if (index++ < offset) continue;
            if (emitted >= 20) { hasMore = true; break; }
            const QString processName = QString::fromUtf16(
                reinterpret_cast<const ushort *>(name.Ptr()), name.Length());
            // Neutralise control characters before entering our line protocol.
            QString clean = processName.left(100);
            for (int j = 0; j < clean.size(); ++j) {
                const ushort unit = clean.at(j).unicode();
                if (unit < 32 || unit > 126) clean[j] = QChar('?');
            }
            result << clean;
            ++emitted;
        }
        if (hasMore) result << "[NEXT] " + QString::number(offset + emitted);
        else result << "[END]";
        sendB64(result.join("\n"));
#else
        Q_UNUSED(offset);
        sendLine("ERR SYMBIAN_ONLY");
#endif
    }
    // Snapshotted in the phone process, reported only to the authenticated
    // Debian endpoint. HAL RAM values are bytes. The public power-state
    // properties (0x10205041, keys 1..3) expose vendor-specific RAW integers,
    // not a battery percentage. Missing/denied reads are "unavailable".
    // This does not subscribe to or modify system properties.
    static QString metricValue(TInt error, TInt value) {
        return error == KErrNone ? QString::number(value) : QString("unavailable");
    }
    void sendMetrics() {
#ifdef Q_OS_SYMBIAN
        QStringList values;
        TInt ramTotal = 0;
        TInt ramFree = 0;
        const TInt ramTotalErr = HAL::Get(HALData::EMemoryRAM, ramTotal);
        const TInt ramFreeErr = HAL::Get(HALData::EMemoryRAMFree, ramFree);
        values << "ram_total_bytes=" + metricValue(ramTotalErr, ramTotal);
        values << "ram_free_bytes=" + metricValue(ramFreeErr, ramFree);
        const TUid category = TUid::Uid(0x10205041); // Symbian HWRM power P&S
        TInt level = 0;
        TInt battery = 0;
        TInt charging = 0;
        const TInt levelErr = RProperty::Get(category, 1, level);
        const TInt batteryErr = RProperty::Get(category, 2, battery);
        const TInt chargingErr = RProperty::Get(category, 3, charging);
        values << "battery_level_raw=" + metricValue(levelErr, level);
        values << "battery_status_raw=" + metricValue(batteryErr, battery);
        values << "charging_status_raw=" + metricValue(chargingErr, charging);
        sendB64(values.join("\n"));
#else
        sendLine("ERR SYMBIAN_ONLY");
#endif
    }
    bool openProbe(QFile *file, qint64 *length) {
        const QString fixedPath = QString::fromLatin1(kProbePath);
        const QFileInfo info(fixedPath);
        if (!info.exists() || !info.isFile() || info.isSymLink()) {
            sendLine("ERR PROBE_NOT_FOUND"); return false;
        }
        // Resolve aliases for defence-in-depth. The source path is hard-coded.
        const QString canonical = QDir::cleanPath(info.canonicalFilePath());
        if (canonical.isEmpty() ||
            canonical.compare(fixedPath, Qt::CaseInsensitive) != 0) {
            sendLine("ERR PROBE_PATH_REJECTED"); return false;
        }
        if (info.size() < 0 || info.size() > kProbeLimit) {
            sendLine("ERR PROBE_TOO_LARGE"); return false;
        }
        file->setFileName(fixedPath);
        if (!file->open(QIODevice::ReadOnly)) {
            sendLine("ERR PROBE_UNREADABLE"); return false;
        }
        if (file->size() != info.size()) {
            sendLine("ERR PROBE_CHANGED"); return false;
        }
        *length = info.size();
        return true;
    }
    void sendProbeInfo() {
        QFile probe;
        qint64 length = 0;
        if (!openProbe(&probe, &length)) return;
        E7Sha256State hash;
        e7_sha256_init(&hash);
        qint64 readCount = 0;
        while (readCount < length) {
            const qint64 wanted = qMin(static_cast<qint64>(2048), length - readCount);
            const QByteArray block = probe.read(wanted);
            if (block.isEmpty()) { sendLine("ERR PROBE_READ_FAILED"); return; }
            e7_sha256_update(&hash,
                reinterpret_cast<const unsigned char *>(block.constData()),
                static_cast<unsigned int>(block.size()));
            readCount += block.size();
        }
        if (probe.size() != length) { sendLine("ERR PROBE_CHANGED"); return; }
        unsigned char digest[32];
        e7_sha256_final(&hash, digest);
        const QByteArray hex = QByteArray(reinterpret_cast<const char *>(digest), 32).toHex();
        sendB64("size=" + QString::number(length) + "\nsha256=" +
                QString::fromLatin1(hex.constData()));
    }
    void sendProbeChunk(qint64 offset) {
        QFile probe;
        qint64 length = 0;
        if (!openProbe(&probe, &length)) return;
        if (offset >= length || !probe.seek(offset)) {
            sendLine("ERR PROBE_OFFSET"); return;
        }
        const qint64 wanted = qMin(kProbeChunk, length - offset);
        const QByteArray block = probe.read(wanted);
        if (block.size() != wanted || probe.size() != length) {
            sendLine("ERR PROBE_CHANGED"); return;
        }
        // QByteArray::toBase64 is binary-safe; never turn the chunk into QString.
        sendLine("B64 " + block.toBase64());
    }
    void sendB64(const QString &text) {
        const QByteArray encoded = text.toUtf8().toBase64();
        if (encoded.size() > kMaxLine - 8) {
            sendLine("ERR RESPONSE_TOO_LONG");
            return;
        }
        sendLine("B64 " + encoded);
    }
    void listDir(const QString &requested) {
        QString path;
        if (!resolvedPath(requested, &path)) {
            sendLine("ERR PATH_NOT_ALLOWED_OR_MISSING");
            return;
        }
        const QDir dir(path);
        if (!dir.exists() || !dir.isReadable()) {
            sendLine("ERR NOT_READABLE_OR_MISSING");
            return;
        }
        QStringList lines;
        const QFileInfoList entries = dir.entryInfoList(
            QDir::AllEntries | QDir::NoDotAndDotDot,
            QDir::DirsFirst | QDir::Name);
        for (int i = 0; i < entries.size() && lines.size() < 50; ++i) {
            const QFileInfo &entry = entries.at(i);
            const QString name = entry.fileName();
            const QString lowered = name.toLower();
            if (lowered == "private" || lowered == "sys" ||
                lowered == "resource" || entry.isSymLink()) continue;
            lines << ((entry.isDir() ? "[D] " : "[F] ") + name.left(100));
        }
        if (entries.size() > 50) lines << "... more entries exist";
        sendB64(lines.join("\n"));
    }
    void statPath(const QString &requested) {
        QString path;
        if (!resolvedPath(requested, &path)) {
            sendLine("ERR PATH_NOT_ALLOWED_OR_MISSING");
            return;
        }
        const QFileInfo entry(path);
        if (!entry.isReadable()) {
            sendLine("ERR NOT_READABLE");
            return;
        }
        QString details = (entry.isDir() ? "directory" : "file");
        if (entry.isFile()) details += " | bytes=" + QString::number(entry.size());
        details += " | path=" + path;
        sendB64(details);
    }
private:
    static QString pairingSettingsPath() {
        // On Symbian, QApplication::applicationDirPath() resolves to
        // the application's private, Secure-ID-caged directory on C:.
        // Do NOT use QSettings UserScope: its default path is public on Symbian.
        return QApplication::applicationDirPath() + "/e7bridge-connection.ini";
    }
    void restoreSavedPairing() {
        QSettings saved(pairingSettingsPath(), QSettings::IniFormat);
        saved.setFallbacksEnabled(false);
        const QString address = saved.value("connection/host").toString().trimmed();
        const QString secret = saved.value("connection/pairing_key").toString().trimmed().toLower();
        const QHostAddress addr(address);
        if (!addr.isNull() && addr.protocol() == QAbstractSocket::IPv4Protocol &&
            QRegExp("[0-9a-f]{16}").exactMatch(secret)) {
            server->setText(address);
            key->setText(secret);
            state->setText("Saved pairing loaded. Press Connect manually.");
        }
    }
    bool savePairing() {
        const QString address = server->text().trimmed();
        const QString secret = key->text().trimmed().toLower();
        const QHostAddress addr(address);
        if (addr.isNull() || addr.protocol() != QAbstractSocket::IPv4Protocol ||
            !QRegExp("[0-9a-f]{16}").exactMatch(secret)) return false;
        QSettings saved(pairingSettingsPath(), QSettings::IniFormat);
        saved.setFallbacksEnabled(false);
        saved.setValue("connection/host", address);
        saved.setValue("connection/pairing_key", secret);
        saved.sync();
        return saved.status() == QSettings::NoError;
    }
    bool clearSavedPairing() {
        QSettings saved(pairingSettingsPath(), QSettings::IniFormat);
        saved.setFallbacksEnabled(false);
        saved.clear(); // Only touches this app's own private connection.ini.
        saved.sync();
        return saved.status() == QSettings::NoError;
    }
    E7BridgeApplication *bridgeApp;
    QLineEdit *server;
    QLineEdit *key;
    QCheckBox *remember;
    QLabel *state;
    QTcpSocket *socket;
    QNetworkSession *session;
    QByteArray incoming;
    QByteArray challengeNonce;
    bool authenticated;
    bool awaitingReady;
    bool wantConnection;
    int adminSequence;
    bool uploadActive;
    QFile uploadFile;
    QString uploadTemp;
    QString uploadTarget;
    QByteArray uploadExpected;
    qint64 uploadSize;
    qint64 uploadReceived;
    E7Sha256State uploadHash;
};

int main(int argc, char *argv[]) {
    E7BridgeApplication app(argc, argv);
    E7Bridge bridge(&app);
    bridge.showMaximized();
    return app.exec();
}

#include "main.moc"
