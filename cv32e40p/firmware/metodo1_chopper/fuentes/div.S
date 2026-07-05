// CHOPPER (referencia wfi) - categoria DIV (division, ~21 ciclos, contada por
// DIVCYC en el modelo hibrido). Alterna fase DIV (GPIO alto) con fase IDLE =
// core dormido (wfi). delta del ESP32 = dinamica de DIV sobre la estatica.
// Auto-contenido.
#include "platform.inc"

#define CHOP_PAIRS 500
#define CAT_ITERS  2200         // ~0.3 s (div stallea fuerte -> pocas iter/0.3s)
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

    li a1, 0x7FFFFF01            // dividendo / divisor (operandos de la categoria)
    li a2, 0x000037A1

    li s0, CHOP_PAIRS
chop_loop:
    gpio_high
    li s1, CAT_ITERS
cat_phase:
    .rept 16
    div  t0, a1, a2
    divu t1, a1, a2
    rem  t2, a1, a2
    remu t3, a1, a2
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
