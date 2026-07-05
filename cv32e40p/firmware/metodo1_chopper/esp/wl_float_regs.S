#ifndef REPS
#define REPS 500000
#endif

#include "/home/jjsotoch/pulp/tfg-pulpissimo/cv32e40p/firmware/caracterizacion/benchmarks/platform.inc"

.section .text
.globl run_workload
.type run_workload, @function
run_workload:
    .option push
    .option norvc

    li t0, 0x6000
    csrs mstatus, t0
    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)

    li s0, REPS
1:
    .rept 8
    fadd.s ft2, ft0, ft1
    fsub.s ft3, ft2, ft1
    fmul.s ft4, ft3, ft0
    fadd.s ft5, ft4, ft2
    fsub.s ft6, ft5, ft3
    fmul.s ft7, ft6, ft1
    fadd.s ft2, ft7, ft4
    fsub.s ft3, ft2, ft0
    .endr
    addi s0, s0, -1
    bnez s0, 1b

    .option pop
    ret

.section .data
.align 4
float_words:
    .word 0x3f800000, 0x40000000
