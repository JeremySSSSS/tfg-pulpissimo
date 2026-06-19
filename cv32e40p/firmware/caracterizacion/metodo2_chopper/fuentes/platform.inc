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

# --- FC timer e ITC: referencia idle WFI (core clock-gated) ---------------
# El FC timer (dominio de periferico) sigue corriendo con el core dormido y al
# llegar a CMP genera el evento 10 -> despierta el wfi. irq_i[10] es valida en
# este cv32e40p (IRQ_MASK=0xFFFFFFFF). Con mstatus.MIE=0 el wfi DESPIERTA pero
# no toma trap (patron wait_for_event_noirq de pulp-runtime).
.equ FC_TIMER_BASE,    0x1A10B000
.equ TIMER_CFG_LO,     0x00          # ENABLE|RESET|IRQEN|MODE
.equ TIMER_CMP_LO,     0x10          # valor de comparacion (ticks)
.equ FC_ITC_BASE,      0x1A109800
.equ ITC_MASK_SET,     0x04
.equ ITC_MASK_CLR,     0x08
.equ ITC_STATUS_CLR,   0x14
.equ TIMER_EVT_BIT,    (1 << 10)     # evento FC timer LO = id 10
.equ TIMER_CFG_RUN,    ((1<<0)|(1<<1)|(1<<2)|(1<<4))  # enable|reset|irqen|cycle

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

# Habilita la linea de irq del FC timer LO en el core (mie[10]). mstatus.MIE
# queda en 0 -> el wfi despierta con el evento pero NO salta a un handler.
.macro enable_timer_wakeup
    li t0, TIMER_EVT_BIT
    csrs mie, t0
.endm

# Fase IDLE pasiva REAL: arma el FC timer para \ticks y duerme el core con wfi.
# El core se clock-gatea (conmutacion ~0, mejor linea base que el bucle de NOPs
# a IPC~1). Usa a3/a4/a5 para no pisar los operandos de la categoria (t0/t1, a1/a2).
.macro wfi_idle ticks
    li a4, TIMER_EVT_BIT
    li a3, FC_ITC_BASE
    sw a4, ITC_STATUS_CLR(a3)        # limpia evento pendiente
    li a3, FC_TIMER_BASE
    li a5, \ticks
    sw a5, TIMER_CMP_LO(a3)          # CMP = ticks
    li a5, TIMER_CFG_RUN
    sw a5, TIMER_CFG_LO(a3)          # arranca (resetea cuenta, irq on)
    li a3, FC_ITC_BASE
    sw a4, ITC_MASK_SET(a3)          # habilita evento 10 al core
    wfi                              # core dormido hasta el evento del timer
    sw a4, ITC_MASK_CLR(a3)          # despierto: deshabilita
    sw a4, ITC_STATUS_CLR(a3)        # limpia
    li a3, FC_TIMER_BASE
    sw zero, TIMER_CFG_LO(a3)        # apaga el timer
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
