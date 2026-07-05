/* RGB -> Y (luma) en assembly: FLOAT + MEM realista con FP SEGURO.
 * Por pixel: 3 flw frescos, 3 fmul INDEPENDIENTES y 2 fadd en arbol de
 * profundidad 2; pixeles independientes entre si (sin acumulador FP entre
 * iteraciones, sin fmadd/fcvt). Cadena mas larga = 2 (fmul->fadd->fadd),
 * un paso mas que el patron probado de wl_dotprod (flw->fmul). */
#ifndef REPS
#define REPS 1500
#endif
#define NP 1024

.section .data
.align 4
rgb:                          /* NP pixeles R,G,B intercalados */
    .rept NP
    .word 0x3f800000, 0x3f000000, 0x3e800000   /* 1.0, 0.5, 0.25 */
    .endr
coef_y_r:  .word 0x3e991687   /* 0.299f */
coef_y_g:  .word 0x3f16960b   /* 0.587f */
coef_y_b:  .word 0x3de978d5   /* 0.114f */

.section .bss
.align 4
luma:
    .space NP*4

.section .text
.globl run_workload
.type run_workload, @function
run_workload:
    .option push
    .option norvc

    li t0, 0x6000
    csrs mstatus, t0
    la t0, coef_y_r
    flw ft0, 0(t0)
    la t0, coef_y_g
    flw ft1, 0(t0)
    la t0, coef_y_b
    flw ft2, 0(t0)

    li s0, REPS
1:
    la t1, rgb
    la t2, luma
    li t3, NP
2:
    flw ft3, 0(t1)            /* R */
    flw ft4, 4(t1)            /* G */
    flw ft5, 8(t1)            /* B */
    fmul.s ft6, ft3, ft0      /* independientes entre si */
    fmul.s ft7, ft4, ft1
    fmul.s ft8, ft5, ft2
    fadd.s ft9, ft6, ft7      /* arbol: profundidad 2 */
    fadd.s ft10, ft9, ft8
    fsw ft10, 0(t2)
    addi t1, t1, 12
    addi t2, t2, 4
    addi t3, t3, -1
    bnez t3, 2b
    addi s0, s0, -1
    bnez s0, 1b

    .option pop
    ret
.size run_workload, .-run_workload
