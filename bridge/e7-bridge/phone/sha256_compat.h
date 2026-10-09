#ifndef E7_BRIDGE_SHA256_COMPAT_H
#define E7_BRIDGE_SHA256_COMPAT_H

// Portable SHA-256/HMAC-SHA256 for the historical Qt 4.7.4 Symbian SDK.
// Qt 4.7 QCryptographicHash offers SHA-1 but not SHA-256. This implementation
// uses only C++98 and unsigned 32-bit words; no OpenSSL or external DLL.
// Wire protocol compatibility: HMAC key/message are the raw input bytes.

typedef unsigned int E7Word32;
typedef char E7Requires32BitUnsignedInt[((~0U) == 0xffffffffU) ? 1 : -1];

struct E7Sha256State {
    E7Word32 h[8];
    E7Word32 bitsHigh;
    E7Word32 bitsLow;
    unsigned char block[64];
    unsigned int used;
};

static inline E7Word32 e7_rotr(E7Word32 x, unsigned int n) {
    return (x >> n) | (x << (32U - n));
}

static inline void e7_sha256_transform(E7Sha256State *ctx) {
    static const E7Word32 k[64] = {
        0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U,
        0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
        0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U,
        0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
        0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
        0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
        0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
        0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
        0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U,
        0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
        0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U,
        0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
        0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U,
        0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
        0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
        0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U
    };
    E7Word32 w[64];
    unsigned int i;
    for (i = 0; i < 16; ++i) {
        const unsigned int j = i * 4U;
        w[i] = ((E7Word32)ctx->block[j] << 24) |
               ((E7Word32)ctx->block[j + 1] << 16) |
               ((E7Word32)ctx->block[j + 2] << 8) |
               ((E7Word32)ctx->block[j + 3]);
    }
    for (i = 16; i < 64; ++i) {
        const E7Word32 x = w[i - 15];
        const E7Word32 y = w[i - 2];
        const E7Word32 s0 = e7_rotr(x, 7) ^ e7_rotr(x, 18) ^ (x >> 3);
        const E7Word32 s1 = e7_rotr(y, 17) ^ e7_rotr(y, 19) ^ (y >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    E7Word32 a = ctx->h[0], b = ctx->h[1], c = ctx->h[2], d = ctx->h[3];
    E7Word32 e = ctx->h[4], f = ctx->h[5], g = ctx->h[6], h = ctx->h[7];
    for (i = 0; i < 64; ++i) {
        const E7Word32 s1 = e7_rotr(e, 6) ^ e7_rotr(e, 11) ^ e7_rotr(e, 25);
        const E7Word32 choice = (e & f) ^ ((~e) & g);
        const E7Word32 t1 = h + s1 + choice + k[i] + w[i];
        const E7Word32 s0 = e7_rotr(a, 2) ^ e7_rotr(a, 13) ^ e7_rotr(a, 22);
        const E7Word32 majority = (a & b) ^ (a & c) ^ (b & c);
        const E7Word32 t2 = s0 + majority;
        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }
    ctx->h[0] += a; ctx->h[1] += b; ctx->h[2] += c; ctx->h[3] += d;
    ctx->h[4] += e; ctx->h[5] += f; ctx->h[6] += g; ctx->h[7] += h;
}

static inline void e7_sha256_init(E7Sha256State *ctx) {
    static const E7Word32 initial[8] = {
        0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U, 0xa54ff53aU,
        0x510e527fU, 0x9b05688cU, 0x1f83d9abU, 0x5be0cd19U
    };
    for (unsigned int i = 0; i < 8; ++i) ctx->h[i] = initial[i];
    ctx->bitsHigh = ctx->bitsLow = 0;
    ctx->used = 0;
}

static inline void e7_sha256_update(E7Sha256State *ctx,
                                    const unsigned char *data,
                                    unsigned int size) {
    const E7Word32 oldLow = ctx->bitsLow;
    ctx->bitsLow += ((E7Word32)size << 3);
    ctx->bitsHigh += ((E7Word32)size >> 29) +
                     (ctx->bitsLow < oldLow ? 1U : 0U);
    for (unsigned int i = 0; i < size; ++i) {
        ctx->block[ctx->used++] = data[i];
        if (ctx->used == 64U) {
            e7_sha256_transform(ctx);
            ctx->used = 0;
        }
    }
}

static inline void e7_sha256_final(E7Sha256State *ctx,
                                   unsigned char digest[32]) {
    ctx->block[ctx->used++] = 0x80;
    if (ctx->used > 56U) {
        while (ctx->used < 64U) ctx->block[ctx->used++] = 0;
        e7_sha256_transform(ctx);
        ctx->used = 0;
    }
    while (ctx->used < 56U) ctx->block[ctx->used++] = 0;
    for (unsigned int i = 0; i < 4; ++i) {
        ctx->block[56 + i] = (unsigned char)(ctx->bitsHigh >> (24 - i * 8));
        ctx->block[60 + i] = (unsigned char)(ctx->bitsLow >> (24 - i * 8));
    }
    e7_sha256_transform(ctx);
    for (unsigned int i = 0; i < 8; ++i) {
        digest[i * 4] = (unsigned char)(ctx->h[i] >> 24);
        digest[i * 4 + 1] = (unsigned char)(ctx->h[i] >> 16);
        digest[i * 4 + 2] = (unsigned char)(ctx->h[i] >> 8);
        digest[i * 4 + 3] = (unsigned char)(ctx->h[i]);
    }
}

static inline void e7_sha256(const unsigned char *data, unsigned int size,
                             unsigned char digest[32]) {
    E7Sha256State ctx;
    e7_sha256_init(&ctx);
    e7_sha256_update(&ctx, data, size);
    e7_sha256_final(&ctx, digest);
}

static inline void e7_hmac_sha256(const unsigned char *key,
                                  unsigned int keySize,
                                  const unsigned char *message,
                                  unsigned int messageSize,
                                  unsigned char digest[32]) {
    unsigned char keyBlock[64];
    unsigned char inner[32];
    unsigned int i;
    for (i = 0; i < 64; ++i) keyBlock[i] = 0;
    if (keySize > 64U) {
        e7_sha256(key, keySize, keyBlock);
    } else {
        for (i = 0; i < keySize; ++i) keyBlock[i] = key[i];
    }
    E7Sha256State ctx;
    for (i = 0; i < 64; ++i) keyBlock[i] ^= 0x36U;
    e7_sha256_init(&ctx);
    e7_sha256_update(&ctx, keyBlock, 64);
    e7_sha256_update(&ctx, message, messageSize);
    e7_sha256_final(&ctx, inner);
    for (i = 0; i < 64; ++i) keyBlock[i] ^= (0x36U ^ 0x5cU);
    e7_sha256_init(&ctx);
    e7_sha256_update(&ctx, keyBlock, 64);
    e7_sha256_update(&ctx, inner, 32);
    e7_sha256_final(&ctx, digest);
}

#endif // E7_BRIDGE_SHA256_COMPAT_H
