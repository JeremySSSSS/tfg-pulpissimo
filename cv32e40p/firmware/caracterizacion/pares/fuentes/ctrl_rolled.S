// PAR DIFERENCIAL CTRL (enrollado: un salto tomado por cuerpo): dos variantes identicas salvo la categoria en
// disputa; el coeficiente se despeja de la RESTA de energias:
//   e = (E_A - E_B) / (n_A - n_B),  E_i = (P_i - P_idle) * T_i
// Es un tercer camino independiente de M1 (aislamiento) y M2 (regresion).
#include "platform.inc"

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
    reset_category_counters
    li s0, 28800000
    gpio_high
    li t0, 0x7A3F158B
    li t1, 0xC49E2D87
    li t2, 0x5D18B3E9
    li t3, 0xA7C46F21
    csrr s1, mcycle
measurement_loop:
    add  a4, t0, t1
    xor  a5, t1, t2
    slli a4, t3, 3
    addi s0, s0, -1
    bnez s0, measurement_loop
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
.section .bss
.align 4
.globl results
results:
    .space 72
