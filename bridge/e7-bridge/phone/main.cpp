// E7 Bridge v0.4.0: native Qt 4.7.4 agent for Nokia Belle.
// Manually launched, read-only, outbound TCP, HMAC authenticated.
// Never writes files, executes shell commands, or runs at boot.
#include <QtGui/QApplication>
#include <QtGui/QWidget>
#include <QtGui/QLabel>
#include <QtGui/QLineEdit>
#include <QtGui/QPushButton>
#include <QtGui/QVBoxLayout>
#include <QtGui/QFormLayout>
#include <QtNetwork/QTcpSocket>
#include <QtNetwork/QHostAddress>
#include <QtNetwork/QNetworkSession>
#include <QtNetwork/QNetworkConfigurationManager>
#include "sha256_compat.h"
#include <QtCore/QDir>
#include <QtCore/QFileInfo>
#include <QtCore/QRegExp>
#include <QtCore/QStringList>
#ifdef Q_OS_SYMBIAN
#include <e32base.h> // TFindProcess and TFullName enumerate process names read-only
#include <e32property.h> // RProperty::Get; read only
#include <hal.h> // HAL::Get; read only
#endif

static const int kPort = 46270;
static const int kMaxLine = 4096;

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

class E7Bridge : public QWidget {
    Q_OBJECT
public:
    E7Bridge(QWidget *parent = 0)
        : QWidget(parent), socket(new QTcpSocket(this)), session(0),
          authenticated(false), awaitingReady(false), wantConnection(false) {
        setWindowTitle("E7 Bridge");
        QLabel *intro = new QLabel(
            "E7 Bridge v0.4.0\nRead-only control over local Wi-Fi", this);
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
        QPushButton *connectButton = new QPushButton("Connect", this);
        QPushButton *disconnectButton = new QPushButton("Disconnect", this);
        state = new QLabel("Idle; nothing runs in the background.", this);
        state->setWordWrap(true);
        QVBoxLayout *layout = new QVBoxLayout(this);
        layout->addWidget(intro);
        layout->addLayout(form);
        layout->addWidget(connectButton);
        layout->addWidget(disconnectButton);
        layout->addWidget(state);
        connect(connectButton, SIGNAL(clicked()), this, SLOT(startLink()));
        connect(disconnectButton, SIGNAL(clicked()), this, SLOT(stopLink()));
        connect(socket, SIGNAL(connected()), this, SLOT(onConnected()));
        connect(socket, SIGNAL(disconnected()), this, SLOT(onDisconnected()));
        connect(socket, SIGNAL(readyRead()), this, SLOT(onData()));
        connect(socket, SIGNAL(error(QAbstractSocket::SocketError)),
                this, SLOT(onSocketError(QAbstractSocket::SocketError)));
    }
private slots:
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
        wantConnection = true;
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
        wantConnection = false;
        socket->abort();
        authenticated = false;
        awaitingReady = false;
        incoming.clear();
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
        wantConnection = false;
        authenticated = false;
        awaitingReady = false;
        incoming.clear();
        key->setEnabled(true);
        state->setText("Disconnected. Reconnect manually when ready.");
    }
    void onSocketError(QAbstractSocket::SocketError) {
        wantConnection = false;
        state->setText("Network error: " + socket->errorString());
    }
    void onSessionError(QNetworkSession::SessionError) {
        wantConnection = false;
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
            awaitingReady = false;
            key->setEnabled(false);
            state->setText("Authenticated. Debian terminal connected (read-only).");
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
        if (line == "PING") { sendLine("OK PONG"); return; }
        if (line == "INFO") {
            sendLine("OK Nokia Belle; Qt " + QByteArray(QT_VERSION_STR) +
                     "; E7 Bridge v0.4.0");
            return;
        }
        if (line == "METRICS") { sendMetrics(); return; }
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
    QLineEdit *server;
    QLineEdit *key;
    QLabel *state;
    QTcpSocket *socket;
    QNetworkSession *session;
    QByteArray incoming;
    QByteArray challengeNonce;
    bool authenticated;
    bool awaitingReady;
    bool wantConnection;
};

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);
    E7Bridge bridge;
    bridge.showMaximized();
    return app.exec();
}

#include "main.moc"
