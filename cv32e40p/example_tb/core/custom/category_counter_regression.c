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

#define WRITE_CSR(csr, value)         \
  asm volatile("csrw " STR(csr) ", %0"\
               :                      \
               : "r"(value))

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

static volatile uint32_t data_word = 0xA5A55A5A;

static inline __attribute__((always_inline)) void reset_category_counters(void)
{
    /*
     * Keep the arithmetic counter reset last. Some CSR instructions can pass
     * through the ALU path; writing ARITH last prevents reset traffic from
     * polluting the arithmetic measurement window.
     */
    asm volatile(RESET_COUNTERS_ASM ::: "memory");
}

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

static int test_csr_read_write(void)
{
    int errors = 0;
    uint32_t arith;
    uint32_t logic;
    uint32_t memory;
    uint32_t branch;
    uint32_t jump;
    uint32_t floating;

    asm volatile(
        RESET_COUNTERS_ASM
        "li   t0, 0x11\n"
        "csrw " STR(CSR_CAT_ARITH) ", t0\n"
        "csrr %0, " STR(CSR_CAT_ARITH) "\n"
        : "=r"(arith)
        :
        : "t0", "memory");

    asm volatile(
        RESET_COUNTERS_ASM
        "li   t0, 0x22\n"
        "csrw " STR(CSR_CAT_LOGIC) ", t0\n"
        "csrr %0, " STR(CSR_CAT_LOGIC) "\n"
        : "=r"(logic)
        :
        : "t0", "memory");

    asm volatile(
        RESET_COUNTERS_ASM
        "li   t0, 0x33\n"
        "csrw " STR(CSR_CAT_MEMORY) ", t0\n"
        "csrr %0, " STR(CSR_CAT_MEMORY) "\n"
        : "=r"(memory)
        :
        : "t0", "memory");

    asm volatile(
        RESET_COUNTERS_ASM
        "li   t0, 0x44\n"
        "csrw " STR(CSR_CAT_BRANCH) ", t0\n"
        "csrr %0, " STR(CSR_CAT_BRANCH) "\n"
        : "=r"(branch)
        :
        : "t0", "memory");

    asm volatile(
        RESET_COUNTERS_ASM
        "li   t0, 0x55\n"
        "csrw " STR(CSR_CAT_JUMP) ", t0\n"
        "csrr %0, " STR(CSR_CAT_JUMP) "\n"
        : "=r"(jump)
        :
        : "t0", "memory");

    asm volatile(
        RESET_COUNTERS_ASM
        "li   t0, 0x66\n"
        "csrw " STR(CSR_CAT_FLOAT) ", t0\n"
        "csrr %0, " STR(CSR_CAT_FLOAT) "\n"
        : "=r"(floating)
        :
        : "t0", "memory");

    errors += expect_eq("csr arith write/read",  arith,    0x11);
    errors += expect_eq("csr logic write/read",  logic,    0x22);
    errors += expect_eq("csr memory write/read", memory,   0x33);
    errors += expect_eq("csr branch write/read", branch,   0x44);
    errors += expect_eq("csr jump write/read",   jump,     0x55);
    errors += expect_eq("csr float write/read",  floating, 0x66);

    asm volatile(
        RESET_COUNTERS_ASM
        "csrr %0, " STR(CSR_CAT_ARITH) "\n"
        "csrr %1, " STR(CSR_CAT_LOGIC) "\n"
        "csrr %2, " STR(CSR_CAT_MEMORY) "\n"
        "csrr %3, " STR(CSR_CAT_BRANCH) "\n"
        "csrr %4, " STR(CSR_CAT_JUMP) "\n"
        "csrr %5, " STR(CSR_CAT_FLOAT) "\n"
        : "=r"(arith), "=r"(logic), "=r"(memory), "=r"(branch), "=r"(jump), "=r"(floating)
        :
        : "memory");

    errors += expect_eq("csr reset arith",  arith,    0);
    errors += expect_eq("csr reset logic",  logic,    0);
    errors += expect_eq("csr reset memory", memory,   0);
    errors += expect_eq("csr reset branch", branch,   0);
    errors += expect_eq("csr reset jump",   jump,     0);
    errors += expect_eq("csr reset float",  floating, 0);

    return errors;
}

static int test_arithmetic_count(void)
{
    uint32_t arith;

    reset_category_counters();

    asm volatile(
        RESET_COUNTERS_ASM
        "li  t0, 7\n"
        "li  t1, 3\n"
        "add t2, t0, t1\n"
        "sub t2, t2, t1\n"
        "mul t2, t0, t1\n"
        "csrr %0, " STR(CSR_CAT_ARITH) "\n"
        : "=r"(arith)
        :
        : "t0", "t1", "t2", "memory");

    return expect_eq("arithmetic block", arith, 5);
}

static int test_logic_count(void)
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

    return expect_eq("logic block", logic, 5);
}

static int test_memory_count(void)
{
    uint32_t memory;
    volatile uint32_t *addr = &data_word;

    asm volatile(
        RESET_COUNTERS_ASM
        "lw   t0, 0(%1)\n"
        "sw   t0, 0(%1)\n"
        "csrr %0, " STR(CSR_CAT_MEMORY) "\n"
        : "=r"(memory)
        : "r"(addr)
        : "t0", "memory");

    return expect_eq("memory block", memory, 2);
}

static int test_branch_count(void)
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

    return expect_eq("branch block", branch, 2);
}

static int test_jump_count(void)
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

    return expect_eq("jump block", jump, 2);
}

static int test_non_target_stability(void)
{
    int errors = 0;
    uint32_t logic;
    uint32_t memory;
    uint32_t branch;
    uint32_t jump;
    uint32_t floating;

    asm volatile(
        RESET_COUNTERS_ASM
        "li  t0, 4\n"
        "li  t1, 2\n"
        "add t2, t0, t1\n"
        "sub t2, t2, t1\n"
        "mul t2, t0, t1\n"
        :
        :
        : "t0", "t1", "t2", "memory");

    logic    = READ_CSR(CSR_CAT_LOGIC);
    memory   = READ_CSR(CSR_CAT_MEMORY);
    branch   = READ_CSR(CSR_CAT_BRANCH);
    jump     = READ_CSR(CSR_CAT_JUMP);
    floating = READ_CSR(CSR_CAT_FLOAT);

    errors += expect_eq("arith-only leaves logic", logic, 0);
    errors += expect_eq("arith-only leaves memory", memory, 0);
    errors += expect_eq("arith-only leaves branch", branch, 0);
    errors += expect_eq("arith-only leaves jump", jump, 0);
    errors += expect_eq("arith-only leaves float", floating, 0);

    return errors;
}

int main(void)
{
    int errors = 0;

    printf("category counter regression\n");

    errors += test_csr_read_write();
    errors += test_arithmetic_count();
    errors += test_logic_count();
    errors += test_memory_count();
    errors += test_branch_count();
    errors += test_jump_count();
    errors += test_non_target_stability();

    if (errors != 0) {
        printf("CATEGORY REGRESSION FAIL errors=%d\n", errors);
        return EXIT_FAILURE;
    }

    printf("CATEGORY REGRESSION PASS\n");
    return EXIT_SUCCESS;
}
