#include <stdint.h>

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

#define WRITE_CSR(csr, value)         \
  asm volatile("csrw " STR(csr) ", %0"\
               :                      \
               : "r"(value))

#define ARCHI_GPIO_ADDR     0x1A101000u
#define ARCHI_PAD_CFG_ADDR  0x1A121000u

#define GPIO_MODE0_ADDR     (ARCHI_GPIO_ADDR + 0x008u)
#define GPIO_SET0_ADDR      (ARCHI_GPIO_ADDR + 0x200u)
#define GPIO_CLEAR0_ADDR    (ARCHI_GPIO_ADDR + 0x280u)
#define PAD_IO08_CFG_ADDR   (ARCHI_PAD_CFG_ADDR + 0x044u)
#define PAD_IO08_MUX_ADDR   (ARCHI_PAD_CFG_ADDR + 0x048u)

#define PAD_MODE_GPIO       0x0Eu
#define PAD_CFG_CHIP2PAD    (1u << 0)
#define PAD_CFG_TX_EN       (1u << 3)
#define GPIO08_MODE_OUTPUT  (1u << 16)
#define GPIO08_BIT          (1u << 8)

#define MMIO32(addr) (*(volatile uint32_t *)(addr))

static volatile uint32_t data_word = 0x2468ACE0;

static void power_mark_init(void)
{
    MMIO32(PAD_IO08_MUX_ADDR) = PAD_MODE_GPIO;
    MMIO32(PAD_IO08_CFG_ADDR) = PAD_CFG_CHIP2PAD | PAD_CFG_TX_EN;
    MMIO32(GPIO_MODE0_ADDR)   = GPIO08_MODE_OUTPUT;
    MMIO32(GPIO_CLEAR0_ADDR)  = GPIO08_BIT;
}

static inline void power_mark_start(void)
{
    MMIO32(GPIO_SET0_ADDR) = GPIO08_BIT;
}

static inline void power_mark_stop(void)
{
    MMIO32(GPIO_CLEAR0_ADDR) = GPIO08_BIT;
}

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
    power_mark_init();
    reset_category_counters();
    power_mark_start();

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

    power_mark_stop();

    asm volatile(
        "wfi\n"
        "3: j 3b\n");

    __builtin_unreachable();
}
