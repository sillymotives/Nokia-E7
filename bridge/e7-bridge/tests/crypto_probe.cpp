// Native test adapter around the EXACT header compiled into the Nokia app.
#include "../phone/sha256_compat.h"
extern "C" void e7_test_sha256(const unsigned char *message,
                                 unsigned int size,
                                 unsigned char digest[32]) {
    e7_sha256(message, size, digest);
}
extern "C" void e7_test_hmac(const unsigned char *key,
                               unsigned int keySize,
                               const unsigned char *message,
                               unsigned int messageSize,
                               unsigned char digest[32]) {
    e7_hmac_sha256(key, keySize, message, messageSize, digest);
}
