/* FLOAT + CTRL: FP independiente (set probado fadd/fmul/fsub/fmax, operandos
 * ft0/ft1 fijos) con saltos DATA-DEPENDENT decididos por un xorshift entero
 * (impredecibles -> mezcla taken/not-taken). Valida e_float con e_ctrl. */
#ifndef REPS
#define REPS 2500000
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

    li t0, 0x2545F491       /* semilla xorshift */
    li s0, REPS
1:
    /* xorshift32: t0 = t0 ^ (t0<<13) ^ (t0>>17) ^ (t0<<5) */
    slli t1, t0, 13
    xor  t0, t0, t1
    srli t1, t0, 17
    xor  t0, t0, t1
    slli t1, t0, 5
    xor  t0, t0, t1

    andi t2, t0, 1
    beqz t2, 2f
    fadd.s ft2, ft0, ft1
    fmul.s ft3, ft0, ft1
    j 3f
2:
    fsub.s ft4, ft1, ft0
    fmax.s ft5, ft0, ft1
3:
    andi t2, t0, 2
    beqz t2, 4f
    fmul.s ft6, ft1, ft1
4:
    addi s0, s0, -1
    bnez s0, 1b

    .option pop
    ret
.size run_workload, .-run_workload
