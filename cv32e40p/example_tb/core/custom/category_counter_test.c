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

static volatile uint32_t data_word = 0x12345678;

static void reset_category_counters(void)
{
    WRITE_CSR(CSR_CAT_ARITH, 0);
    WRITE_CSR(CSR_CAT_ARITH_HI, 0);
    WRITE_CSR(CSR_CAT_LOGIC, 0);
    WRITE_CSR(CSR_CAT_LOGIC_HI, 0);
    WRITE_CSR(CSR_CAT_MEMORY, 0);
    WRITE_CSR(CSR_CAT_MEMORY_HI, 0);
    WRITE_CSR(CSR_CAT_BRANCH, 0);
    WRITE_CSR(CSR_CAT_BRANCH_HI, 0);
    WRITE_CSR(CSR_CAT_JUMP, 0);
    WRITE_CSR(CSR_CAT_JUMP_HI, 0);
    WRITE_CSR(CSR_CAT_FLOAT, 0);
    WRITE_CSR(CSR_CAT_FLOAT_HI, 0);
}

int main(void)
{
    uint32_t arithmetic;
    uint32_t logic;
    uint32_t memory;
    uint32_t branch;
    uint32_t jump;
    uint32_t floating;

    reset_category_counters();

    asm volatile(
        "li t0, 7\n"
        "li t1, 3\n"
        "add t2, t0, t1\n"
        "sub t2, t2, t1\n"
        "mul t2, t0, t1\n"
        "and t3, t0, t1\n"
        "or  t3, t3, t0\n"
        "xor t3, t3, t1\n"
        "lw  t4, 0(%0)\n"
        "sw  t4, 0(%0)\n"
        "beq t0, t0, 1f\n"
        "addi t5, zero, 1\n"
        "1:\n"
        "jal 2f\n"
        "addi t5, zero, 2\n"
        "2:\n"
        :
        : "r"(&data_word)
        : "t0", "t1", "t2", "t3", "t4", "t5", "memory");

    arithmetic = READ_CSR(CSR_CAT_ARITH);
    logic      = READ_CSR(CSR_CAT_LOGIC);
    memory     = READ_CSR(CSR_CAT_MEMORY);
    branch     = READ_CSR(CSR_CAT_BRANCH);
    jump       = READ_CSR(CSR_CAT_JUMP);
    floating   = READ_CSR(CSR_CAT_FLOAT);

    printf("category counters\n");
    printf("arith=%lu\n", (unsigned long)arithmetic);
    printf("logic=%lu\n", (unsigned long)logic);
    printf("memory=%lu\n", (unsigned long)memory);
    printf("branch=%lu\n", (unsigned long)branch);
    printf("jump=%lu\n", (unsigned long)jump);
    printf("float=%lu\n", (unsigned long)floating);

    return EXIT_SUCCESS;
}
