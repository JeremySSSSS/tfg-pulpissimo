.equ GPIO_MODE0,      0x1A101008
.equ GPIO_SET0,       0x1A101200
.equ GPIO_CLEAR0,     0x1A101280
.equ PAD_IO08_CFG,     0x1A121044
.equ PAD_IO08_MUX,     0x1A121048
.equ PAD_IO09_CFG,     0x1A12104C
.equ PAD_IO09_MUX,     0x1A121050
.equ PAD_IO10_CFG,     0x1A121054
.equ PAD_IO10_MUX,     0x1A121058
.equ PAD_IO11_CFG,     0x1A12105C
.equ PAD_IO11_MUX,     0x1A121060

.equ GPIO08_BIT,       (1 << 8)
.equ GPIO08_MODE_OUT,  (1 << 16)
.equ LED_BITS,         ((1 << 9) | (1 << 10) | (1 << 11))
.equ LED_MODE_OUT,     ((1 << 18) | (1 << 20) | (1 << 22))
.equ PAD_IO08_GPIO,    14
.equ PAD_IO09_GPIO,    14
.equ PAD_IO10_GPIO,    14
.equ PAD_IO11_GPIO,    14
.equ PAD_CFG_OUTPUT,   ((1 << 3) | (1 << 0))

.equ CSR_CAT_ARITH_LO,  0xBC0
.equ CSR_CAT_ARITH_HI,  0xBC1
.equ CSR_CAT_LOGIC_LO,  0xBC2
.equ CSR_CAT_LOGIC_HI,  0xBC3
.equ CSR_CAT_MEMORY_LO, 0xBC4
.equ CSR_CAT_MEMORY_HI, 0xBC5
.equ CSR_CAT_BRANCH_LO, 0xBC6
.equ CSR_CAT_BRANCH_HI, 0xBC7
.equ CSR_CAT_JUMP_LO,   0xBC8
.equ CSR_CAT_JUMP_HI,   0xBC9
.equ CSR_CAT_FLOAT_LO,  0xBCA
.equ CSR_CAT_FLOAT_HI,  0xBCB

.macro gpio_init
    li t0, PAD_IO08_MUX
    li t1, PAD_IO08_GPIO
    sw t1, 0(t0)

    li t0, PAD_IO08_CFG
    li t1, PAD_CFG_OUTPUT
    sw t1, 0(t0)

    li t0, GPIO_MODE0
    li t1, GPIO08_MODE_OUT
    sw t1, 0(t0)

    li t0, GPIO_CLEAR0
    li t1, GPIO08_BIT
    sw t1, 0(t0)
.endm

.macro gpio_high
    li t0, GPIO_SET0
    li t1, GPIO08_BIT
    sw t1, 0(t0)
.endm

.macro gpio_low
    li t0, GPIO_CLEAR0
    li t1, GPIO08_BIT
    sw t1, 0(t0)
.endm

.macro led_init
    li t0, PAD_IO09_MUX
    li t1, PAD_IO09_GPIO
    sw t1, 0(t0)
    li t0, PAD_IO09_CFG
    li t1, PAD_CFG_OUTPUT
    sw t1, 0(t0)

    li t0, PAD_IO10_MUX
    li t1, PAD_IO10_GPIO
    sw t1, 0(t0)
    li t0, PAD_IO10_CFG
    li t1, PAD_CFG_OUTPUT
    sw t1, 0(t0)

    li t0, PAD_IO11_MUX
    li t1, PAD_IO11_GPIO
    sw t1, 0(t0)
    li t0, PAD_IO11_CFG
    li t1, PAD_CFG_OUTPUT
    sw t1, 0(t0)

    li t0, GPIO_MODE0
    li t1, LED_MODE_OUT
    sw t1, 0(t0)

    li t0, GPIO_CLEAR0
    li t1, LED_BITS
    sw t1, 0(t0)
.endm

.macro led_high
    li t0, GPIO_SET0
    li t1, LED_BITS
    sw t1, 0(t0)
.endm

.macro led_low
    li t0, GPIO_CLEAR0
    li t1, LED_BITS
    sw t1, 0(t0)
.endm

.macro reset_category_counters
    csrw CSR_CAT_ARITH_LO, zero
    csrw CSR_CAT_ARITH_HI, zero
    csrw CSR_CAT_LOGIC_LO, zero
    csrw CSR_CAT_LOGIC_HI, zero
    csrw CSR_CAT_MEMORY_LO, zero
    csrw CSR_CAT_MEMORY_HI, zero
    csrw CSR_CAT_BRANCH_LO, zero
    csrw CSR_CAT_BRANCH_HI, zero
    csrw CSR_CAT_JUMP_LO, zero
    csrw CSR_CAT_JUMP_HI, zero
    csrw CSR_CAT_FLOAT_LO, zero
    csrw CSR_CAT_FLOAT_HI, zero
.endm
