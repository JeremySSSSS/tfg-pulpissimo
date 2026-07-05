/* MD5 (RFC 1321): hash criptografico estandar, uso masivo (checksums, firmas,
 * integridad). Algoritmo REAL. Perfil ALU/logica (F/G/H/I) + rotaciones + sumas
 * + MEM (mensaje M[16], tablas K/S). Entero puro, sin FP, sin libc. Hashea un
 * bloque de 512 bits REPS veces variando la entrada para que el lazo no se pliegue. */
#ifndef REPS
#define REPS 120000
#endif

typedef unsigned int u32;
typedef unsigned char u8;

#define ROTL(x, n) (((x) << (n)) | ((x) >> (32 - (n))))

static const u32 K[64] = {
  0xd76aa478,0xe8c7b756,0x242070db,0xc1bdceee,0xf57c0faf,0x4787c62a,0xa8304613,0xfd469501,
  0x698098d8,0x8b44f7af,0xffff5bb1,0x895cd7be,0x6b901122,0xfd987193,0xa679438e,0x49b40821,
  0xf61e2562,0xc040b340,0x265e5a51,0xe9b6c7aa,0xd62f105d,0x02441453,0xd8a1e681,0xe7d3fbc8,
  0x21e1cde6,0xc33707d6,0xf4d50d87,0x455a14ed,0xa9e3e905,0xfcefa3f8,0x676f02d9,0x8d2a4c8a,
  0xfffa3942,0x8771f681,0x6d9d6122,0xfde5380c,0xa4beea44,0x4bdecfa9,0xf6bb4b60,0xbebfbc70,
  0x289b7ec6,0xeaa127fa,0xd4ef3085,0x04881d05,0xd9d4d039,0xe6db99e5,0x1fa27cf8,0xc4ac5665,
  0xf4292244,0x432aff97,0xab9423a7,0xfc93a039,0x655b59c3,0x8f0ccc92,0xffeff47d,0x85845dd1,
  0x6fa87e4f,0xfe2ce6e0,0xa3014314,0x4e0811a1,0xf7537e82,0xbd3af235,0x2ad7d2bb,0xeb86d391
};
static const u8 S[64] = {
  7,12,17,22, 7,12,17,22, 7,12,17,22, 7,12,17,22,
  5, 9,14,20, 5, 9,14,20, 5, 9,14,20, 5, 9,14,20,
  4,11,16,23, 4,11,16,23, 4,11,16,23, 4,11,16,23,
  6,10,15,21, 6,10,15,21, 6,10,15,21, 6,10,15,21
};

static u32 H[4];
static u32 M[16];          /* un bloque de 512 bits */

static void md5_block(void) {
  u32 a = H[0], b = H[1], c = H[2], d = H[3];
  for (int i = 0; i < 64; i++) {
    u32 f; int g;
    if (i < 16)      { f = (b & c) | (~b & d);        g = i; }
    else if (i < 32) { f = (d & b) | (~d & c);        g = (5*i + 1) & 15; }
    else if (i < 48) { f = b ^ c ^ d;                 g = (3*i + 5) & 15; }
    else             { f = c ^ (b | ~d);              g = (7*i) & 15; }
    f = f + a + K[i] + M[g];
    a = d; d = c; c = b;
    b = b + ROTL(f, S[i]);
  }
  H[0] += a; H[1] += b; H[2] += c; H[3] += d;
}

void run_workload(void) {
  unsigned s = 2463534242u;
  for (int i = 0; i < 16; i++) { s^=s<<13; s^=s>>17; s^=s<<5; M[i] = s; }

  volatile u32 sink = 0;
  for (int rep = 0; rep < REPS; rep++) {
    H[0]=0x67452301; H[1]=0xefcdab89; H[2]=0x98badcfe; H[3]=0x10325476;
    md5_block();
    sink ^= H[0];
    M[rep & 15] ^= (u32)rep;        /* varia la entrada */
  }
  (void)sink;
}
