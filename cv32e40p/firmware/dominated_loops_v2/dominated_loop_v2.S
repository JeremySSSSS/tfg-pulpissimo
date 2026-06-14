// Bucle dominado por categoria para el clasificador v2 (medicion fisica).
// Un .S parametrico: se compila una vez por categoria con -DCATEGORY_<X>.
// 64 instrucciones objetivo por iteracion (16 rept x 4) + addi/bnez de
// control. Los cuerpos son los mismos verificados en simulacion
// (clasif_v2/loop_*.S). Ventana de medicion = flanco de GPIO8 (-> ESP32).
// Al final vuelca los 16 CSR + mcycle ini/fin a 'results' (leer por JTAG).
#include "platform.inc"

#ifndef LOOP_COUNT
#define LOOP_COUNT 2000000
#endif

#if !defined(CATEGORY_ALU)  && !defined(CATEGORY_MUL)  && \
    !defined(CATEGORY_MULH) && !defined(CATEGORY_DIV)  && \
    !defined(CATEGORY_MEM)  && !defined(CATEGORY_CTRL) && \
    !defined(CATEGORY_FLOAT)&& !defined(CATEGORY_IDLE)
#error "Define exactamente un CATEGORY_* (ALU/MUL/MULH/DIV/MEM/CTRL/FLOAT/IDLE)"
#endif

.section .text.start
.globl _start
.type _start, @function
_start:
    .option push
    .option norvc

    la sp, __stack_top
    la t0, trap_handler
    csrw mtvec, t0

    gpio_init

    /* Habilita mcycle (mcountinhibit.CY = 0). */
    csrci 0x320, 1

#ifdef CATEGORY_FLOAT
    /* Marca el estado FP como inicializado y carga operandos FP. */
    li t0, 0x6000
    csrs mstatus, t0
    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)
#endif

    reset_category_counters
    li s0, LOOP_COUNT

    /* La ventana medida la define el flanco de GPIO8. */
    gpio_high

    /* Operandos de la categoria (una sola vez, dentro de la ventana:
       aporte despreciable frente a LOOP_COUNT*64). */
#if defined(CATEGORY_ALU) || defined(CATEGORY_MUL) || defined(CATEGORY_MULH)
    li t0, 0x12345
    li t1, 0x06789
#endif
#ifdef CATEGORY_DIV
    li a1, 0x7FFFFF01      /* dividendo */
    li a2, 0x000037A1      /* divisor (no nulo) */
#endif
#ifdef CATEGORY_MEM
    la s2, data_words      /* buffer; s2 se reusa como mcycle_fin despues */
    li a2, 0xABCD1234      /* dato a escribir */
#endif

    csrr s1, mcycle

measurement_loop:
#ifdef CATEGORY_ALU
    .rept 16
    addi t0, t0, 1
    xor  t1, t1, t0
    slli t2, t0, 2
    add  t3, t1, t2
    .endr
#endif
#ifdef CATEGORY_MUL
    .rept 16
    mul  t2, t0, t1
    mul  t3, t2, t0
    mul  t4, t3, t1
    mul  t5, t4, t0
    .endr
#endif
#ifdef CATEGORY_MULH
    .rept 16
    mulh   t2, t0, t1
    mulhu  t3, t0, t1
    mulhsu t4, t0, t1
    mulh   t5, t2, t1
    .endr
#endif
#ifdef CATEGORY_DIV
    .rept 16
    div  t0, a1, a2
    divu t1, a1, a2
    rem  t2, a1, a2
    remu t3, a1, a2
    .endr
#endif
#ifdef CATEGORY_MEM
    .rept 8
    sw   a2, 0(s2)
    sw   a2, 4(s2)
    sw   a2, 8(s2)
    sw   a2, 12(s2)
    lw   t0, 0(s2)
    lw   t1, 4(s2)
    lw   t2, 8(s2)
    lw   t3, 12(s2)
    .endr
#endif
#ifdef CATEGORY_CTRL
    .rept 64
    j    . + 4
    .endr
#endif
#ifdef CATEGORY_FLOAT
    .rept 16
    fadd.s ft2, ft0, ft1
    fmul.s ft3, ft0, ft1
    fsub.s ft4, ft1, ft0
    fmax.s ft5, ft2, ft3
    .endr
#endif
#ifdef CATEGORY_IDLE
    /* sin cuerpo: solo el control del bucle (linea base) */
#endif

    addi s0, s0, -1
    bnez s0, measurement_loop

    csrr s2, mcycle
    gpio_low

    dump_counters

finished:
    ebreak
    wfi
    j finished

trap_handler:
    ebreak
    j trap_handler

    .option pop
.size _start, .-_start

.section .data
.align 4
data_words:
    .word 0x11111111, 0x22222222, 0, 0, 0, 0

.align 4
float_words:
    .word 0x3f800000, 0x40000000

.section .bss
.align 4
.globl results
results:
    .space 72
