/*
 * Mezclas balanceadas para regresion por energia.
 * Cada perfil activa las 7 categorias y añade overhead filtrado para romper
 * la dependencia entre T y los conteos.
 */
#include "platform.inc"

#ifndef PROFILE
#error "Defina PROFILE=0..11"
#endif
#ifndef LOOP_COUNT
#define LOOP_COUNT 300000
#endif

.macro ops_overhead blocks
    .rept \blocks
        csrr zero, mcycle
        csrr zero, mcycle
        csrr zero, mcycle
        csrr zero, mcycle
    .endr
.endm

.macro ops_alu blocks
    .rept \blocks
        addi a4, a4, 1
        xor  a5, a5, a4
        slli a6, a4, 2
        add  a7, a5, a6
    .endr
.endm

.macro ops_mul blocks
    .rept \blocks
        mul t2, t0, t1
        mul t3, t1, t0
        mul t4, t0, t0
        mul t5, t1, t1
    .endr
.endm

.macro ops_mulh blocks
    .rept \blocks
        mulh   t2, t0, t1
        mulhu  t3, t0, t1
        mulhsu t4, t0, t1
        mulh   t5, t1, t0
    .endr
.endm

.macro ops_div blocks
    .rept \blocks
        div  t2, a1, a2
        divu t3, a1, a2
        rem  t4, a1, a2
        remu t5, a1, a2
    .endr
.endm

.macro ops_mem blocks
    .rept \blocks
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

.macro ops_ctrl blocks
    .rept \blocks
        j . + 4
        j . + 4
        j . + 4
        j . + 4
    .endr
.endm

.macro ops_float blocks
    .rept \blocks
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
    csrr s1, mcycle

loop_body:
#if PROFILE == 0
    ops_overhead 2
    ops_alu 10
    ops_mul 8
    ops_mulh 1
    ops_div 1
    ops_mem 1
    ops_ctrl 1
    ops_float 1
#elif PROFILE == 1
    ops_overhead 2
    ops_alu 1
    ops_mul 10
    ops_mulh 8
    ops_div 1
    ops_mem 1
    ops_ctrl 1
    ops_float 1
#elif PROFILE == 2
    ops_overhead 2
    ops_alu 1
    ops_mul 1
    ops_mulh 10
    ops_div 8
    ops_mem 1
    ops_ctrl 1
    ops_float 1
#elif PROFILE == 3
    ops_overhead 2
    ops_alu 1
    ops_mul 1
    ops_mulh 1
    ops_div 10
    ops_mem 8
    ops_ctrl 1
    ops_float 1
#elif PROFILE == 4
    ops_overhead 2
    ops_alu 1
    ops_mul 1
    ops_mulh 1
    ops_div 1
    ops_mem 10
    ops_ctrl 8
    ops_float 1
#elif PROFILE == 5
    ops_overhead 2
    ops_alu 1
    ops_mul 1
    ops_mulh 1
    ops_div 1
    ops_mem 1
    ops_ctrl 10
    ops_float 8
#elif PROFILE == 6
    ops_overhead 2
    ops_alu 8
    ops_mul 1
    ops_mulh 1
    ops_div 1
    ops_mem 1
    ops_ctrl 1
    ops_float 10
#elif PROFILE == 7
    ops_overhead 2
    ops_alu 4
    ops_mul 4
    ops_mulh 4
    ops_div 4
    ops_mem 4
    ops_ctrl 4
    ops_float 4
#elif PROFILE == 8
    ops_overhead 2
    ops_alu 7
    ops_mul 2
    ops_mulh 7
    ops_div 2
    ops_mem 7
    ops_ctrl 2
    ops_float 7
#elif PROFILE == 9
    ops_overhead 2
    ops_alu 2
    ops_mul 7
    ops_mulh 2
    ops_div 7
    ops_mem 2
    ops_ctrl 7
    ops_float 2
#elif PROFILE == 10
    ops_overhead 2
    ops_alu 5
    ops_mul 1
    ops_mulh 9
    ops_div 5
    ops_mem 1
    ops_ctrl 9
    ops_float 1
#elif PROFILE == 11
    ops_overhead 2
    ops_alu 1
    ops_mul 5
    ops_mulh 1
    ops_div 9
    ops_mem 5
    ops_ctrl 1
    ops_float 9
#else
#error "PROFILE fuera de rango"
#endif

    addi s0, s0, -1
    bnez s0, loop_body

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
