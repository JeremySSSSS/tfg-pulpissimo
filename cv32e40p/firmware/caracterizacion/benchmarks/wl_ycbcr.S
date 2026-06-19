/* RGB -> YCbCr en assembly: FP simple, independiente, sin FMA ni fcvt. */
#ifndef REPS
#define REPS 1000
#endif
#define NP 4096
#include "platform.inc"

.section .data
.align 4
rgb:
    .rept NP
    .word 0x3f800000
    .endr
.align 4
coef_y_r:  .word 0x3e991687  /* 0.299f */
coef_y_g:  .word 0x3f16960b  /* 0.587f */
coef_y_b:  .word 0x3de978d5  /* 0.114f */
coef_c_r:  .word 0xbe2c8b44  /* -0.168736f */
coef_c_g:  .word 0xbea9fbe7  /* -0.331264f */
coef_c_b:  .word 0x3f000000  /* 0.5f */
coef_cr_r: .word 0x3f000000  /* 0.5f */
coef_cr_g: .word 0xbed6d3c7  /* -0.418688f */
coef_cr_b: .word 0xbda64c2f  /* -0.081312f */
coef_off:  .word 0x43000000  /* 128.0f */

.section .bss
.align 4
outv:
    .space 16

.section .text
.globl run_workload
.type run_workload, @function
run_workload:
    .option push
    .option norvc
    li t0, 0x6000
    csrs mstatus, t0
    la t1, rgb
    la t2, coef_y_r
    la t3, coef_y_g
    la t4, coef_y_b
    la t5, coef_c_r
    la t6, coef_c_g
    la s0, coef_c_b
    la s1, coef_cr_r
    la s2, coef_cr_g
    la s3, coef_cr_b
    la s4, coef_off
    la s5, outv
    li s6, REPS
rep_loop:
    li s7, NP
pix_loop:
    flw f2, 0(t1)
    flw f3, 0(t1)
    flw f4, 0(t1)
    flw f5, 0(t2)
    flw f6, 0(t3)
    flw f7, 0(t4)
    flw f8, 0(t5)
    flw f9, 0(t6)
    flw f10, 0(s0)
    flw f11, 0(s1)
    flw f12, 0(s2)
    flw f13, 0(s3)
    flw f14, 0(s4)

    fmul.s f15, f2, f5
    fmul.s f16, f3, f6
    fmul.s f17, f4, f7
    fadd.s f15, f15, f16
    fadd.s f15, f15, f17
    fadd.s f15, f15, f14

    fmul.s f16, f2, f8
    fmul.s f17, f3, f9
    fmul.s f18, f4, f10
    fadd.s f16, f16, f17
    fadd.s f16, f16, f18
    fadd.s f16, f16, f14

    fmul.s f17, f2, f11
    fmul.s f18, f3, f12
    fmul.s f19, f4, f13
    fadd.s f17, f17, f18
    fadd.s f17, f17, f19
    fadd.s f17, f17, f14

    fsw f15, 0(s5)
    fsw f16, 4(s5)
    fsw f17, 8(s5)

    addi t1, t1, 4
    addi s7, s7, -1
    bnez s7, pix_loop
    addi s6, s6, -1
    bnez s6, rep_loop
    .option pop
    ret
