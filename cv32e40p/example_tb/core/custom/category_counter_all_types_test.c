#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define CSR_CAT_ARITH     0xBC0
#define CSR_CAT_ARITH_HI  0xBC1
#define CSR_CAT_LOGIC     0xBC2
#define CSR_CAT_LOGIC_HI  0xBC3
#define CSR_CAT_MEMORY    0xBC4
#define CSR_CAT_MEMORY_HI 0xBC5
#define CSR_CAT_BRANCH    0xBC6
#define CSR_CAT_BRANCH_HI 0xBC7
#define CSR_CAT_JUMP      0xBC8
#define CSR_CAT_JUMP_HI   0xBC9
#define CSR_CAT_FLOAT     0xBCA
#define CSR_CAT_FLOAT_HI  0xBCB

#define STR_HELPER(x) #x
#define STR(x) STR_HELPER(x)

#define READ_CSR(csr)                 \
  ({                                  \
    uint32_t value;                   \
    asm volatile("csrr %0, " STR(csr) \
                 : "=r"(value));      \
    value;                            \
  })

#define RESET_COUNTERS_ASM                 \
    "csrw " STR(CSR_CAT_LOGIC)     ", zero\n" \
    "csrw " STR(CSR_CAT_LOGIC_HI)  ", zero\n" \
    "csrw " STR(CSR_CAT_MEMORY)    ", zero\n" \
    "csrw " STR(CSR_CAT_MEMORY_HI) ", zero\n" \
    "csrw " STR(CSR_CAT_BRANCH)    ", zero\n" \
    "csrw " STR(CSR_CAT_BRANCH_HI) ", zero\n" \
    "csrw " STR(CSR_CAT_JUMP)      ", zero\n" \
    "csrw " STR(CSR_CAT_JUMP_HI)   ", zero\n" \
    "csrw " STR(CSR_CAT_FLOAT)     ", zero\n" \
    "csrw " STR(CSR_CAT_FLOAT_HI)  ", zero\n" \
    "csrw " STR(CSR_CAT_ARITH)     ", zero\n" \
    "csrw " STR(CSR_CAT_ARITH_HI)  ", zero\n"

static volatile uint32_t data_word = 0x13579BDF;

static int expect_eq(const char *name, uint32_t got, uint32_t expected)
{
    if (got != expected) {
        printf("FAIL %s: got=%lu expected=%lu\n",
               name, (unsigned long)got, (unsigned long)expected);
        return 1;
    }

    printf("PASS %s: %lu\n", name, (unsigned long)got);
    return 0;
}

static int test_arithmetic(void)
{
    uint32_t arith;

    asm volatile(
        RESET_COUNTERS_ASM
        "li  t0, 9\n"
        "li  t1, 4\n"
        "add t2, t0, t1\n"
        "sub t2, t2, t1\n"
        "mul t2, t0, t1\n"
        "csrr %0, " STR(CSR_CAT_ARITH) "\n"
        : "=r"(arith)
        :
        : "t0", "t1", "t2", "memory");

    return expect_eq("arith", arith, 5);
}

static int test_logic(void)
{
    uint32_t logic;

    asm volatile(
        RESET_COUNTERS_ASM
        "li   t0, 0x55\n"
        "li   t1, 0x0f\n"
        "and  t2, t0, t1\n"
        "or   t2, t2, t0\n"
        "xor  t2, t2, t1\n"
        "slli t2, t2, 1\n"
        "srli t2, t2, 1\n"
        "csrr %0, " STR(CSR_CAT_LOGIC) "\n"
        : "=r"(logic)
        :
        : "t0", "t1", "t2", "memory");

    return expect_eq("logic", logic, 5);
}

static int test_memory(void)
{
    uint32_t memory_count;
    volatile uint32_t *addr = &data_word;

    asm volatile(
        RESET_COUNTERS_ASM
        "lw   t0, 0(%1)\n"
        "sw   t0, 0(%1)\n"
        "csrr %0, " STR(CSR_CAT_MEMORY) "\n"
        : "=r"(memory_count)
        : "r"(addr)
        : "t0", "memory");

    return expect_eq("memory", memory_count, 2);
}

static int test_branch(void)
{
    uint32_t branch;

    asm volatile(
        RESET_COUNTERS_ASM
        "li   t0, 1\n"
        "li   t1, 1\n"
        "beq  t0, t1, 1f\n"
        "addi t2, zero, 99\n"
        "1:\n"
        "bne  t0, t1, 2f\n"
        "2:\n"
        "csrr %0, " STR(CSR_CAT_BRANCH) "\n"
        : "=r"(branch)
        :
        : "t0", "t1", "t2", "memory");

    return expect_eq("branch", branch, 2);
}

static int test_jump(void)
{
    uint32_t jump;

    asm volatile(
        RESET_COUNTERS_ASM
        "jal  t0, 1f\n"
        "addi t1, zero, 99\n"
        "1:\n"
        "jal  t0, 2f\n"
        "addi t1, zero, 88\n"
        "2:\n"
        "csrr %0, " STR(CSR_CAT_JUMP) "\n"
        : "=r"(jump)
        :
        : "t0", "t1", "memory");

    return expect_eq("jump", jump, 2);
}

#if defined(__riscv_flen)
static volatile float zero_f = 0.0f;

static int test_float(void)
{
    uint32_t floating;
    volatile float *zero_ptr = &zero_f;

    asm volatile(
        RESET_COUNTERS_ASM
        "flw      ft0, 0(%1)\n"
        "flw      ft1, 0(%1)\n"
        "fadd.s   ft2, ft0, ft1\n"
        "fmul.s   ft3, ft2, ft1\n"
        "fsub.s   ft4, ft3, ft0\n"
        "csrr %0, " STR(CSR_CAT_FLOAT) "\n"
        : "=r"(floating)
        : "r"(zero_ptr)
        : "ft0", "ft1", "ft2", "ft3", "ft4", "memory");

    return expect_eq("float", floating, 3);
}
#else
static int test_float(void)
{
    uint32_t floating = READ_CSR(CSR_CAT_FLOAT);

    printf("SKIP float: firmware compiled without FPU support\n");
    return expect_eq("float-disabled", floating, 0);
}
#endif

int main(void)
{
    int errors = 0;

    printf("category all types test\n");

    errors += test_arithmetic();
    errors += test_logic();
    errors += test_memory();
    errors += test_branch();
    errors += test_jump();
    errors += test_float();

    if (errors != 0) {
        printf("ALL TYPES TEST FAIL errors=%d\n", errors);
        return EXIT_FAILURE;
    }

    printf("ALL TYPES TEST PASS\n");
    return EXIT_SUCCESS;
}
