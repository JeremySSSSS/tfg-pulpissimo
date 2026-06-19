// CHOPPER (referencia wfi) - categoria MEM (loads/stores a memoria, CPI~2).
// Alterna fase MEM (GPIO alto) con fase IDLE = core dormido (wfi). delta del
// ESP32 = dinamica de MEM sobre la estatica. Auto-contenido.
#include "platform.inc"

#define CHOP_PAIRS 500
#define CAT_ITERS  22900        // ~0.3 s
#define IDLE_TICKS 3000000      // ~0.3 s a 10 MHz

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
    enable_timer_wakeup

    la s2, data_words           // base del buffer / valor a escribir
    li a2, 0xABCD1234

    li s0, CHOP_PAIRS
chop_loop:
    gpio_high
    li s1, CAT_ITERS
cat_phase:
    .rept 8
    sw   a2, 0(s2)
    sw   a2, 4(s2)
    sw   a2, 8(s2)
    sw   a2, 12(s2)
    lw   t0, 0(s2)
    lw   t1, 4(s2)
    lw   t2, 8(s2)
    lw   t3, 12(s2)
    .endr
    addi s1, s1, -1
    bnez s1, cat_phase

    gpio_low
    wfi_idle IDLE_TICKS

    addi s0, s0, -1
    bnez s0, chop_loop

    gpio_low
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
