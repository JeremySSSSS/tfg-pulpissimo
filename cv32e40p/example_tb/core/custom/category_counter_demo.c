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

volatile uint32_t demo_arith  = 0;
volatile uint32_t demo_logic  = 0;
volatile uint32_t demo_memory = 0;
volatile uint32_t demo_branch = 0;
volatile uint32_t demo_jump   = 0;
volatile uint32_t demo_float  = 0;

static volatile uint32_t data_word = 0x2468ACE0;

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
    reset_category_counters();

    asm volatile(
        "li   t0, 8\n"
        "li   t1, 3\n"
        "add  t2, t0, t1\n"
        "sub  t2, t2, t1\n"
        "and  t3, t0, t1\n"
        "xor  t3, t3, t1\n"
        "lw   t4, 0(%0)\n"
        "sw   t4, 0(%0)\n"
        "beq  t0, t0, 1f\n"
        "addi t5, zero, 99\n"
        "1:\n"
        "jal  t6, 2f\n"
        "addi t5, zero, 88\n"
        "2:\n"
        :
        : "r"(&data_word)
        : "t0", "t1", "t2", "t3", "t4", "t5", "t6", "memory");

    demo_arith  = READ_CSR(CSR_CAT_ARITH);
    demo_logic  = READ_CSR(CSR_CAT_LOGIC);
    demo_memory = READ_CSR(CSR_CAT_MEMORY);
    demo_branch = READ_CSR(CSR_CAT_BRANCH);
    demo_jump   = READ_CSR(CSR_CAT_JUMP);
    demo_float  = READ_CSR(CSR_CAT_FLOAT);

    printf("category counter demo\n");
    printf("arith=%lu logic=%lu memory=%lu branch=%lu jump=%lu float=%lu\n",
           (unsigned long)demo_arith,
           (unsigned long)demo_logic,
           (unsigned long)demo_memory,
           (unsigned long)demo_branch,
           (unsigned long)demo_jump,
           (unsigned long)demo_float);

    return EXIT_SUCCESS;
}
