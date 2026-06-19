// CHOPPER (referencia wfi) - categoria CTRL (saltos/control de flujo, CPI~2).
// Alterna fase CTRL (GPIO alto) con fase IDLE = core dormido (wfi). delta del
// ESP32 = dinamica de CTRL sobre la estatica. Auto-contenido.
#include "platform.inc"

#define CHOP_PAIRS 500
#define CAT_ITERS  22700        // ~0.3 s
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

    li s0, CHOP_PAIRS
chop_loop:
    gpio_high
    li s1, CAT_ITERS
cat_phase:
    .rept 64
    j    . + 4                  // salto incondicional a la siguiente instruccion
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

.section .bss
.align 4
.globl results
results:
    .space 72
