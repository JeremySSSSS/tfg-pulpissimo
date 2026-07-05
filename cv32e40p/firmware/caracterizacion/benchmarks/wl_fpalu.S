/* FLOAT + ALU intercalados: FP INDEPENDIENTE (mismo set probado que el float
 * de caracterizacion: fadd/fmul/fsub/fmax sobre ft0/ft1 fijos, sin cadenas
 * seriales ni fmadd/fcvt) mezclado 1:1 con ALU entera. Valida e_float en
 * presencia de e_alu. */
#ifndef REPS
#define REPS 700000
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

    li t0, 0x12345
    li t1, 0x06789
    li s0, REPS
1:
    .rept 16
    fadd.s ft2, ft0, ft1
    addi t0, t0, 1
    fmul.s ft3, ft0, ft1
    xor  t1, t1, t0
    fsub.s ft4, ft1, ft0
    slli t2, t0, 2
    fmax.s ft5, ft2, ft3
    add  t3, t1, t2
    .endr
    addi s0, s0, -1
    bnez s0, 1b

    .option pop
    ret
.size run_workload, .-run_workload
