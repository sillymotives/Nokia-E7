"""Source assertions for Symbian red End key background persistence.

These tests do not pretend to compile or validate Qt/GCCE on the handset.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT / "phone/main.cpp").read_text()
BUILD = (ROOT / "build/in-container.sh").read_text()
PRO = (ROOT / "phone/e7bridge.pro").read_text()


class SymbianBackgroundPersistence(unittest.TestCase):
    def test_native_symbian_filter_only_compiled_on_symbian(self):
        self.assertIn('#include <QtGui/QSymbianEvent>', CPP)
        self.assertIn('#include <w32std.h>', CPP)
        self.assertNotIn('#include <avkon.hrh>', CPP)
        self.assertIn('static const TUint32 KE7EndKeyCloseEvent = 0x101F87F0u;', CPP)
        self.assertRegex(CPP, r'#ifdef Q_OS_SYMBIAN\s+protected:\s+virtual bool symbianEventFilter\(')
        self.assertIn('QSymbianEvent::WindowServerEvent', CPP)
        self.assertIn('event->windowServerEvent()->Type() == KE7EndKeyCloseEvent', CPP)
        self.assertIn('return QApplication::symbianEventFilter(event);', CPP)

    def test_only_authenticated_session_activates_native_intercept(self):
        self.assertIn('if (preserveConnectedSession && event &&', CPP)
        self.assertRegex(CPP, r'authenticated = true;\s+bridgeApp->setPreserveConnectedSession\(true\);')
        # No early enable: connection attempts alone are not enough.
        self.assertEqual(CPP.count('setPreserveConnectedSession(true)'), 1)

    def test_owner_disconnection_clears_background_intercept(self):
        for name in ('stopLink', 'onDisconnected', 'onSocketError', 'onSessionError'):
            self.assertRegex(CPP, r'void ' + name + r'\([^)]*\) \{[^}]*setPreserveConnectedSession\(false\);')

    def test_minimise_and_explicit_exit_are_distinct(self):
        self.assertIn('SLOT(backgroundNow())', CPP)
        self.assertIn('SLOT(exitBridge())', CPP)
        background = CPP.split('void backgroundNow() {', 1)[1].split('void exitBridge() {', 1)[0]
        # Symbian: lower the native window group, not Qt's minimized state.
        self.assertIn('#include <coemain.h>', CPP)
        self.assertIn('#ifdef Q_OS_SYMBIAN', background)
        self.assertIn('CCoeEnv::Static()', background)
        self.assertIn('RootWin().SetOrdinalPosition(-1);', background)
        self.assertNotIn('showMinimized();', background.split('#else', 1)[0])
        # On non-Symbian, preserve the original Qt fallback.
        self.assertIn('showMinimized();', background.split('#else', 1)[1])
        self.assertIn('LIBS += -lhal -lsisregistryclient -lcone -lws32', PRO)
        self.assertRegex(CPP, r'void exitBridge\(\) \{\s+[^}]*stopLink\(\);\s+QApplication::quit\(\);')
        self.assertNotIn('setQuitOnLastWindowClosed(false)', CPP)

    def test_version_uid_capabilities_and_installer_match(self):
        self.assertIn('E7 Bridge v0.8.3', CPP)
        self.assertIn('($uid),0,8,3', BUILD)
        self.assertIn('E7Bridge-v0.8.3.sis', BUILD)
        self.assertIn('TARGET.UID3 = 0xE94B7001', PRO)
        self.assertIn('TARGET.CAPABILITY = NetworkServices ReadUserData WriteUserData', PRO)
        capabilities = next(x for x in PRO.splitlines() if x.strip().startswith('TARGET.CAPABILITY ='))
        self.assertNotIn('AllFiles', capabilities)
        self.assertNotIn('TCB', capabilities)
        self.assertNotIn('autostart', CPP.lower())

    def test_pairing_and_hmac_are_untouched(self):
        self.assertIn('restoreSavedPairing(); // Prefill only; NEVER initiate networking at startup.', CPP)
        self.assertIn('QString::fromLatin1(nonce)', CPP)
        self.assertIn('challengeNonce', CPP)
        self.assertIn('E7B1 READY ', CPP)
        self.assertIn('"admin:" + nonce', CPP)


if __name__ == '__main__':
    unittest.main()
