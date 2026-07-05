#ifndef REPS
#define REPS 40000
#endif
#define N 64

.section .data
.align 4
lv_a:
    .rept N
    .word 0x3f800000
    .endr
lv_b:
    .rept N
    .word 0x40000000
    .endr
lv_c:
    .rept N
    .word 0x40400000
    .endr
lv_d:
    .rept N
    .word 0x40800000
    .endr

.section .text
.globl run_workload
.type run_workload, @function
run_workload:
    .option push
    .option norvc

    li t0, 0x6000
    csrs mstatus, t0
    la s1, lv_a
    la s2, lv_b
    la s3, lv_c
    la s4, lv_d
    li s0, REPS
1:
    li t1, 62
    addi t2, s1, 4
    addi t3, s2, 4
    addi t4, s3, 4
    addi t5, s4, 4
2:
    flw ft0, -4(t2)
    flw ft1, 0(t2)
    flw ft2, 4(t2)
    fadd.s ft3, ft0, ft2
    fmul.s ft4, ft1, ft3
    fsub.s ft5, ft4, ft0
    fmax.s ft6, ft5, ft3
    fsw ft6, 0(t4)
    fadd.s ft0, ft6, ft1
    fsw ft0, 0(t3)
    fmul.s ft2, ft0, ft6
    fsw ft2, 0(t5)
    addi t2, t2, 4
    addi t3, t3, 4
    addi t4, t4, 4
    addi t5, t5, 4
    addi t1, t1, -1
    bnez t1, 2b
    addi s0, s0, -1
    bnez s0, 1b

    .option pop
    ret
