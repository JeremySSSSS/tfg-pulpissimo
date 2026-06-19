#ifndef REPS
#define REPS 80000
#endif
#define N 32

.section .data
.align 4
arr:
    .rept N
    .word 0x3f800000
    .endr
coef0: .word 0x3f800000
coef1: .word 0x40000000
coef2: .word 0x40400000

.section .text
.globl run_workload
.type run_workload, @function
run_workload:
    .option push
    .option norvc

    li t0, 0x6000
    csrs mstatus, t0
    la t1, arr
    la t2, coef0
    la t3, coef1
    la t4, coef2
    flw ft0, 0(t2)
    flw ft1, 0(t3)
    flw ft2, 0(t4)

    li s0, REPS
1:
    mv t5, t1
    li t6, N
2:
    flw ft3, 0(t5)
    fmul.s ft4, ft3, ft0
    fadd.s ft4, ft4, ft1
    fsub.s ft5, ft4, ft2
    fsw ft5, 0(t5)
    addi t5, t5, 4
    addi t6, t6, -1
    bnez t6, 2b
    addi s0, s0, -1
    bnez s0, 1b

    .option pop
    ret
