#ifndef REPS
#define REPS 12000
#endif
#define N 16

.section .data
.align 4
lp_a:
    .rept (N*N)
    .word 0x3f800000
    .endr
lp_x:
    .rept N
    .word 0x3f800000
    .endr
lp_y:
    .rept N
    .word 0x00000000
    .endr
lp_one:
    .word 0x3f800000
lp_two:
    .word 0x40000000

.section .text
.globl run_workload
.type run_workload, @function
run_workload:
    .option push
    .option norvc

    li t0, 0x6000
    csrs mstatus, t0
    la s1, lp_a
    la s2, lp_x
    la s3, lp_y
    la s4, lp_one
    la s5, lp_two

    flw ft0, 0(s4)
    flw ft1, 0(s5)

    li s0, REPS
1:
    li t1, N
    mv t2, s1
    mv t3, s3
2:
    fmv.s ft6, ft0
    li t4, N
    mv t5, s2
3:
    flw ft2, 0(t2)
    flw ft3, 0(t5)
    fmul.s ft4, ft2, ft3
    fadd.s ft6, ft6, ft4
    addi t2, t2, 4
    addi t5, t5, 4
    addi t4, t4, -1
    bnez t4, 3b
    fsw ft6, 0(t3)
    addi t3, t3, 4
    addi t1, t1, -1
    bnez t1, 2b

    li t1, N
    mv t2, s3
    mv t3, s2
4:
    flw ft2, 0(t2)
    fmul.s ft3, ft2, ft1
    fadd.s ft3, ft3, ft0
    fsw ft3, 0(t3)
    addi t2, t2, 4
    addi t3, t3, 4
    addi t1, t1, -1
    bnez t1, 4b

    addi s0, s0, -1
    bnez s0, 1b

    .option pop
    ret
