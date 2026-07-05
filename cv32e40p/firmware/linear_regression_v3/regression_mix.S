/*
 * Perfiles para caracterizacion por regresion lineal con intercepto.
 * Cada ELF ejecuta una mezcla distinta durante ~12 s a 10 MHz.
 */
#include "platform.inc"

#ifndef PROFILE
#error "Defina PROFILE=0..19"
#endif
#ifndef LOOP_COUNT
#define LOOP_COUNT 1000000
#endif

.macro ops_base groups
    /* CSR se filtra del clasificador: aproxima actividad base del core. */
    .rept \groups
    csrr zero, mcycle
    csrr zero, mcycle
    csrr zero, mcycle
    csrr zero, mcycle
    .endr
.endm

.macro ops_alu groups
    .rept \groups
    addi a4, a4, 1
    xor  a5, a5, a4
    slli a6, a4, 2
    add  a7, a5, a6
    .endr
.endm

.macro ops_mul groups
    .rept \groups
    mul t2, t0, t1
    mul t3, t1, t0
    mul t4, t0, t0
    mul t5, t1, t1
    .endr
.endm

.macro ops_mulh groups
    .rept \groups
    mulh   t2, t0, t1
    mulhu  t3, t0, t1
    mulhsu t4, t0, t1
    mulh   t5, t1, t0
    .endr
.endm

.macro ops_div groups
    .rept \groups
    div  t2, a1, a2
    divu t3, a1, a2
    rem  t4, a1, a2
    remu t5, a1, a2
    .endr
.endm

.macro ops_mem groups
    .rept \groups
    sw a4,  0(s3)
    sw a5,  4(s3)
    sw a6,  8(s3)
    sw a7, 12(s3)
    lw t2,  0(s3)
    lw t3,  4(s3)
    lw t4,  8(s3)
    lw t5, 12(s3)
    .endr
.endm

.macro ops_ctrl count
    .rept \count
    j . + 4
    .endr
.endm

.macro ops_float groups
    .rept \groups
    fadd.s ft2, ft0, ft1
    fmul.s ft3, ft0, ft1
    fsub.s ft4, ft1, ft0
    fmax.s ft5, ft0, ft1
    .endr
.endm

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

    /* Mismo estado FP y mismos operandos iniciales en todos los perfiles. */
    li t0, 0x6000
    csrs mstatus, t0
    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)

    li a1, 0x7fffff01
    li a2, 0x000037a1
    li a4, 0x13579
    li a5, 0x2468a
    li a6, 0x31415
    li a7, 0x27182
    la s3, data_words

    reset_category_counters
    li s0, LOOP_COUNT

    gpio_high
    /* gpio_high usa t0/t1; inicializarlos despues del flanco. */
    li t0, 0x12345
    li t1, 0x06789
    csrr s1, mcycle

measurement_loop:
#if PROFILE == 0
    ops_base 8                 /* 32 CSR filtrados */
#elif PROFILE == 1
    ops_alu 8                  /* 32 ALU */
#elif PROFILE == 2
    ops_mul 8                  /* 32 MUL */
#elif PROFILE == 3
    ops_mulh 4                 /* 16 MULH */
#elif PROFILE == 4
    ops_div 1                  /* 4 DIV/REM */
#elif PROFILE == 5
    ops_mem 4                  /* 32 MEM */
#elif PROFILE == 6
    ops_ctrl 32                /* 32 CTRL */
#elif PROFILE == 7
    ops_float 8                /* 32 FLOAT */
#elif PROFILE == 8
    ops_alu 4                  /* 16 ALU + 16 MUL */
    ops_mul 4
#elif PROFILE == 9
    ops_mem 2                  /* 16 MEM + 16 CTRL */
    ops_ctrl 16
#elif PROFILE == 10
    ops_mulh 2                 /* 8 MULH + 4 DIV/REM */
    ops_div 1
#elif PROFILE == 11
    ops_float 4                /* 16 FLOAT + 16 MEM */
    ops_mem 2
#elif PROFILE == 12
    ops_alu 1                  /* mezcla balanceada */
    ops_mul 1
    ops_mulh 1
    ops_div 1
    ops_mem 1
    ops_ctrl 4
    ops_float 1
#elif PROFILE == 13
    ops_alu 2                  /* 8 ALU + 8 CTRL + 8 FLOAT */
    ops_ctrl 8
    ops_float 2
#elif PROFILE == 14
    ops_mul 2                  /* 8 MUL + 8 MEM + 4 DIV/REM */
    ops_mem 1
    ops_div 1
#elif PROFILE == 15
    ops_alu 4                  /* 16 ALU + 4 DIV/REM */
    ops_div 1
#elif PROFILE == 16
    ops_mulh 2                 /* 8 MULH + 16 FLOAT */
    ops_float 4
#elif PROFILE == 17
    ops_mem 2                  /* 16 MEM + 16 MUL */
    ops_mul 4
#elif PROFILE == 18
    ops_base 16                /* 64 CSR filtrados */
#elif PROFILE == 19
    ops_base 32                /* 128 CSR filtrados */
#else
#error "PROFILE fuera de rango"
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
    .word 0, 0, 0, 0
.align 4
float_words:
    .word 0x3f800000, 0x40000000

.section .bss
.align 4
.globl results
results:
    .space 72
