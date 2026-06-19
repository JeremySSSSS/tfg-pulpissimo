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

# Clasificador v2: 8 contadores de 64 bits (pares LO/HI), CSR 0xBC0-0xBCF.
# ALU/MUL/MULH/DIV/MEM/CTRL/FLOAT cuentan instrucciones; DIVCYC cuenta
# ciclos de ocupacion del divisor. Ver DISENO_CLASIFICADOR_V2.md.
.equ CSR_CAT_ALU_LO,    0xBC0
.equ CSR_CAT_ALU_HI,    0xBC1
.equ CSR_CAT_MUL_LO,    0xBC2
.equ CSR_CAT_MUL_HI,    0xBC3
.equ CSR_CAT_MULH_LO,   0xBC4
.equ CSR_CAT_MULH_HI,   0xBC5
.equ CSR_CAT_DIV_LO,    0xBC6
.equ CSR_CAT_DIV_HI,    0xBC7
.equ CSR_CAT_MEM_LO,    0xBC8
.equ CSR_CAT_MEM_HI,    0xBC9
.equ CSR_CAT_CTRL_LO,   0xBCA
.equ CSR_CAT_CTRL_HI,   0xBCB
.equ CSR_CAT_FLOAT_LO,  0xBCC
.equ CSR_CAT_FLOAT_HI,  0xBCD
.equ CSR_CAT_DIVCYC_LO, 0xBCE
.equ CSR_CAT_DIVCYC_HI, 0xBCF

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

# Reset de los 16 CSR del clasificador v2.
.macro reset_category_counters
    csrw CSR_CAT_ALU_LO, zero
    csrw CSR_CAT_ALU_HI, zero
    csrw CSR_CAT_MUL_LO, zero
    csrw CSR_CAT_MUL_HI, zero
    csrw CSR_CAT_MULH_LO, zero
    csrw CSR_CAT_MULH_HI, zero
    csrw CSR_CAT_DIV_LO, zero
    csrw CSR_CAT_DIV_HI, zero
    csrw CSR_CAT_MEM_LO, zero
    csrw CSR_CAT_MEM_HI, zero
    csrw CSR_CAT_CTRL_LO, zero
    csrw CSR_CAT_CTRL_HI, zero
    csrw CSR_CAT_FLOAT_LO, zero
    csrw CSR_CAT_FLOAT_HI, zero
    csrw CSR_CAT_DIVCYC_LO, zero
    csrw CSR_CAT_DIVCYC_HI, zero
.endm

# Lee los 16 CSR en registros (sin stores entremedio, para no contaminar
# MEM) y los vuelca a 'results' junto con mcycle ini/fin (s1/s2).
# results = 18 words: [16 CSR en orden 0xBC0..0xBCF][mcycle_ini][mcycle_fin]
.macro dump_counters
    csrr a0, CSR_CAT_ALU_LO
    csrr a1, CSR_CAT_ALU_HI
    csrr a2, CSR_CAT_MUL_LO
    csrr a3, CSR_CAT_MUL_HI
    csrr a4, CSR_CAT_MULH_LO
    csrr a5, CSR_CAT_MULH_HI
    csrr a6, CSR_CAT_DIV_LO
    csrr a7, CSR_CAT_DIV_HI
    csrr t0, CSR_CAT_MEM_LO
    csrr t1, CSR_CAT_MEM_HI
    csrr t2, CSR_CAT_CTRL_LO
    csrr t3, CSR_CAT_CTRL_HI
    csrr t4, CSR_CAT_FLOAT_LO
    csrr t5, CSR_CAT_FLOAT_HI
    csrr t6, CSR_CAT_DIVCYC_LO
    csrr s3, CSR_CAT_DIVCYC_HI
    la   s4, results
    sw a0,  0(s4)
    sw a1,  4(s4)
    sw a2,  8(s4)
    sw a3, 12(s4)
    sw a4, 16(s4)
    sw a5, 20(s4)
    sw a6, 24(s4)
    sw a7, 28(s4)
    sw t0, 32(s4)
    sw t1, 36(s4)
    sw t2, 40(s4)
    sw t3, 44(s4)
    sw t4, 48(s4)
    sw t5, 52(s4)
    sw t6, 56(s4)
    sw s3, 60(s4)
    sw s1, 64(s4)
    sw s2, 68(s4)
.endm
