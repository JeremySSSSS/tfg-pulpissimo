// M1 - bucle dominado MULH.  ~5 min a 10 MHz (9.3M iter x ~324 cic/iter).
// 64 mulh/mulhu/mulhsu (FSM ~4 ciclos) por iteracion + addi/bnez de control.
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
    li s0, 9300000                  // LOOP_COUNT

    gpio_high

    li t0, 0x12345
    li t1, 0x06789

    csrr s1, mcycle
measurement_loop:
    .rept 16
    mulh   t2, t0, t1
    mulhu  t3, t0, t1
    mulhsu t4, t0, t1
    mulh   t5, t2, t1
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
