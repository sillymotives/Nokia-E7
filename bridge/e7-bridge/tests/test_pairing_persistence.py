"""Source-level guardrails for the Qt4/Symbian saved-pairing candidate.

These checks do not replace compilation or physical handset testing.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CPP = (ROOT / 'phone/main.cpp').read_text()
PRO = (ROOT / 'phone/e7bridge.pro').read_text()
BUILD = (ROOT / 'build/in-container.sh').read_text()


class SavedPairingSafety(unittest.TestCase):
    def test_exact_private_settings_path(self):
        self.assertIn('QApplication::applicationDirPath() + "/e7bridge-connection.ini"', CPP)
        self.assertIn('QSettings::IniFormat', CPP)
        self.assertNotIn('QSettings::UserScope,', CPP)

    def test_restore_populates_only_fields(self):
        method = CPP.split('void restoreSavedPairing()', 1)[1].split('bool savePairing()', 1)[0]
        self.assertIn('server->setText(address)', method)
        self.assertIn('key->setText(secret)', method)
        self.assertIn('QAbstractSocket::IPv4Protocol', method)
        self.assertIn('QRegExp("[0-9a-f]{16}")', method)
        self.assertNotIn('startLink()', method)
        self.assertNotIn('openSocket()', method)
        self.assertNotIn('connectToHost(', method)

    def test_save_only_after_ready_authentication(self):
        block = CPP.split('if (awaitingReady) {',1)[1].split('if (!authenticated) {',1)[0]
        self.assertIn('if (line != expected)', block)
        self.assertLess(block.index('if (line != expected)'),block.index('authenticated = true'))
        self.assertLess(block.index('authenticated = true'),block.index('savePairing()'))
        self.assertIn('if (remember->isChecked())',block)

    def test_handshake_inputs_are_frozen(self):
        body = CPP.split('void startLink()',1)[1].split('void openSocket()',1)[0]
        self.assertIn('server->setEnabled(false)',body)
        self.assertIn('key->setEnabled(false)',body)
        self.assertIn('server->setEnabled(true)',CPP)
        self.assertIn('key->setEnabled(true)',CPP)

    def test_forget_and_opt_out_clear_saved_key(self):
        self.assertIn('void forgetPairing()',CPP)
        self.assertIn('void onRememberToggled(bool enabled)',CPP)
        self.assertIn('saved.clear()',CPP)
        self.assertIn('saved.sync()',CPP)
        self.assertIn('server->clear()',CPP)
        self.assertIn('key->clear()',CPP)

    def test_in_place_upgrade_with_one_basic_write_capability(self):
        self.assertIn('TARGET.UID3 = 0xE94B7001',PRO)
        self.assertIn('TARGET.CAPABILITY = NetworkServices ReadUserData WriteUserData',PRO)
        self.assertIn('E7Bridge-v0.8.0.sis',BUILD)
        self.assertIn('($uid),0,8,0',BUILD)
        self.assertIn('E7 Bridge v0.8.0',CPP)

    def test_network_protocol_does_not_offer_system_mutation(self):
        self.assertNotIn('QProcess',CPP)
        self.assertNotIn('RProperty::Set',CPP)
        self.assertNotIn('HAL::Set',CPP)
        self.assertIn('void handleAdminLine(',CPP)
        self.assertIn('void beginUpload(',CPP)
        self.assertIn('void abortUpload()',CPP)

if __name__ == '__main__':
    unittest.main()
