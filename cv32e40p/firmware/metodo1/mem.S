// M1 - bucle dominado MEM.  ~5 min a 10 MHz (23M iter x ~131 cic/iter).
// 32 sw + 32 lw sobre un buffer en L2 (8 rept x 8) por iteracion + addi/bnez.
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
    li s0, 23000000                 // LOOP_COUNT

    gpio_high

    la s2, data_words              // buffer
    li a2, 0xABCD1234              // dato a escribir

    csrr s1, mcycle
measurement_loop:
    .rept 8
    sw a2, 0(s2)
    sw a2, 4(s2)
    sw a2, 8(s2)
    sw a2, 12(s2)
    lw t0, 0(s2)
    lw t1, 4(s2)
    lw t2, 8(s2)
    lw t3, 12(s2)
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

.section .data
.align 4
data_words:
    .word 0x11111111, 0x22222222, 0, 0, 0, 0

.section .bss
.align 4
.globl results
results:
    .space 72
