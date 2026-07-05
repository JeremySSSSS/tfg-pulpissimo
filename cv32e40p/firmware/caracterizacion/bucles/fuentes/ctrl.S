// M1 - bucle dominado CTRL.  ~5 min a 10 MHz (5.7M iter x 256 instr/iter).
// 256 saltos j .+4 (flush/refetch del pipeline) por iteracion + addi/bnez.
// Desenrollado x4 (vs 64) para que el overhead addi/bnez pese 1-en-256 (0.4%).
// Ventana de medicion = flanco de GPIO8 (-> ESP32). Vuelca 16 CSR + mcycle a 'results'.
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
    csrci 0x320, 1                  // habilita mcycle

    reset_category_counters
    li s0, 5700000                  // LOOP_COUNT

    gpio_high

    csrr s1, mcycle
measurement_loop:
    .rept 256
    j . + 4
    .endr
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
