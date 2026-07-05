/* Validacion fisica: mezcla finita de las siete categorias del modelo. */
#include "platform.inc"

#ifndef LOOP_COUNT
#define LOOP_COUNT 100000
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
    csrci 0x320, 1

    /* Habilita la FPU y prepara operandos constantes. */
    li t0, 0x6000
    csrs mstatus, t0
    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)

    /* Operandos enteros, divisor no nulo y buffer alineado. */
    li a1, 0x7fffff01
    li a2, 0x000037a1
    li a4, 0xabcd1234
    li a5, 0x13579
    li a6, 0x2468a
    la s3, data_words

    reset_category_counters
    li s0, LOOP_COUNT

    gpio_high
    li t0, 0x12345
    li t1, 0x06789
    csrr s1, mcycle

measurement_loop:
    /* 8 ALU. */
    .rept 2
    addi a5, a5, 1
    xor  a6, a6, a5
    slli a7, a5, 2
    add  t6, a6, a7
    .endr

    /* 4 MUL. */
    mul t2, t0, t1
    mul t3, t1, t0
    mul t4, t0, t0
    mul t5, t1, t1

    /* 2 MULH. */
    mulh  t2, t0, t1
    mulhu t3, t0, t1

    /* 2 DIV/REM; el clasificador registra instrucciones y ciclos DIVCYC. */
    div t4, a1, a2
    rem t5, a1, a2

    /* 4 MEM. */
    sw t6, 0(s3)
    lw t2, 0(s3)
    sw a4, 4(s3)
    lw t3, 4(s3)

    /* 4 CTRL tomadas. */
    .rept 4
    j . + 4
    .endr

    /* 4 FLOAT independientes. */
    fadd.s ft2, ft0, ft1
    fmul.s ft3, ft0, ft1
    fsub.s ft4, ft1, ft0
    fmax.s ft5, ft0, ft1

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
    .word 0, 0, 0, 0

.align 4
float_words:
    .word 0x3f800000, 0x40000000

.section .bss
.align 4
.globl results
results:
    .space 72
