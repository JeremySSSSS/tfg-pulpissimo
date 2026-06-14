// Harness fisico para cargas REALES (Metodo 2). Envuelve un kernel
// 'run_workload()' (programa real, mezcla natural de instrucciones) entre la
// ventana GPIO8, y al final vuelca los 16 CSR + mcycle a 'results'
// (0x1c0082c0, 18 words). El kernel se enlaza desde un .c aparte.
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
    csrci 0x320, 1            /* habilita mcycle */

    /* Habilita FP por si el kernel usa float (inofensivo si no). */
    li t0, 0x6000
    csrs mstatus, t0

    reset_category_counters

    gpio_high
    csrr s1, mcycle          /* s1: callee-saved, sobrevive la llamada */

    call run_workload        /* el programa real */

    csrr s2, mcycle
    gpio_low

    dump_counters            /* 16 CSR + s1/s2 -> results */

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
.align 8
.globl results
results:
    .space 72
