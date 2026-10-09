"""Check the Qt 4.7-compatible SHA/HMAC implementation against Python hashlib.

Only the local compiler is used; no Nokia SDK, Docker, network, or phone needed.
"""
import ctypes
import hashlib
import hmac
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class PortableCryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('g++')
        if not compiler:
            raise unittest.SkipTest('Requires a C++ compiler for native SHA verification')
        cls.temp = tempfile.TemporaryDirectory(prefix='e7sha-')
        so = Path(cls.temp.name) / 'libe7sha.so'
        subprocess.run([
            compiler, '-std=c++98', '-Wall', '-Wextra', '-Werror', '-pedantic',
            '-O2', '-fPIC', '-shared', str(ROOT / 'crypto_probe.cpp'),
            '-o', str(so)
        ], check=True)
        cls.lib = ctypes.CDLL(str(so))
        cls.lib.e7_test_sha256.argtypes = [
            ctypes.c_char_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_ubyte)
        ]
        cls.lib.e7_test_hmac.argtypes = [
            ctypes.c_char_p, ctypes.c_uint, ctypes.c_char_p, ctypes.c_uint,
            ctypes.POINTER(ctypes.c_ubyte)
        ]

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'temp'):
            cls.temp.cleanup()

    @classmethod
    def hash(cls, data):
        out = (ctypes.c_ubyte * 32)()
        cls.lib.e7_test_sha256(data, len(data), out)
        return bytes(out)

    @classmethod
    def mac(cls, key, message):
        out = (ctypes.c_ubyte * 32)()
        cls.lib.e7_test_hmac(key, len(key), message, len(message), out)
        return bytes(out)

    def test_fips_sha256_examples(self):
        self.assertEqual(self.hash(b'').hex(),
                         'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
        self.assertEqual(self.hash(b'abc').hex(),
                         'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_rfc4231_hmac_sha256_vectors(self):
        self.assertEqual(self.mac(b'\x0b' * 20, b'Hi There').hex(),
                         'b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7')
        self.assertEqual(self.mac(b'Jefe', b'what do ya want for nothing?').hex(),
                         '5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843')

    def test_python_interoperability_over_block_boundaries(self):
        rng = random.Random(7108474)
        sizes = (0, 1, 7, 16, 55, 56, 63, 64, 65, 80, 127, 128, 129, 256, 1023)
        for size in sizes:
            message = bytes(rng.randrange(256) for _ in range(size))
            self.assertEqual(self.hash(message), hashlib.sha256(message).digest())
            for keySize in (0, 1, 16, 64, 65, 100):
                key = bytes(rng.randrange(256) for _ in range(keySize))
                self.assertEqual(self.mac(key, message), hmac.digest(key, message, 'sha256'))

    def test_actual_bridge_handshake_wire_bytes(self):
        key = b'0123456789abcdef'  # ASCII hex key, not decoded hex bytes
        nonce = b'0123456789abcdef0123456789abcdef'
        for prefix in (b'device:', b'host:'):
            message = prefix + nonce
            self.assertEqual(self.mac(key, message).hex(),
                             hmac.new(key, message, hashlib.sha256).hexdigest())


if __name__ == '__main__':
    unittest.main()
