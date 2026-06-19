// CHOPPER (referencia wfi) - categoria MUL (multiplicacion baja, 1 ciclo).
// Alterna fase MUL (GPIO alto) con fase IDLE = core dormido (wfi). delta del
// ESP32 = dinamica de MUL sobre la estatica. Auto-contenido.
#include "platform.inc"

#define CHOP_PAIRS 500
#define CAT_ITERS  44000        // ~0.3 s
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

    li t0, 0x12345
    li t1, 0x06789

    li s0, CHOP_PAIRS
chop_loop:
    gpio_high
    li s1, CAT_ITERS
cat_phase:
    .rept 16
    mul  t2, t0, t1
    mul  t3, t2, t0
    mul  t4, t3, t1
    mul  t5, t4, t0
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
