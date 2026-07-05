#ifndef REPS
#define REPS 200
#endif

.section .data
.align 4
float_words:
    .word 0x3f800000, 0x40000000

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
measurement_loop:
    .rept 64
    fadd.s ft2, ft0, ft1
    fmul.s ft3, ft0, ft1
    fsub.s ft4, ft1, ft0
    fmax.s ft5, ft2, ft3
    .endr
    addi s0, s0, -1
    bnez s0, measurement_loop

    .option pop
    ret
