// CHOPPER (referencia wfi) - categoria ALU.
// Mide la potencia dinamica de ALU por medicion diferencial: alterna CHOP_PAIRS
// veces la fase ALU (GPIO alto) con una fase IDLE = core dormido (wfi, clock-
// gated). El ESP32 bina por estado del GPIO y reporta delta = P(alto) - P(bajo)
// = dinamica de ALU sobre la estatica. Auto-contenido (solo incluye platform.inc).
#include "platform.inc"

#define CHOP_PAIRS 500          // pares categoria/idle (~5 min total)
#define CAT_ITERS  44000        // iteraciones de la fase categoria (~0.3 s)
#define IDLE_TICKS 3000000      // ticks del FC timer en la fase idle (~0.3 s a 10 MHz)

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
    enable_timer_wakeup            // mie[10]=1; mstatus.MIE=0 -> wfi despierta sin trap

    li t0, 0x12345                 // operandos de la categoria
    li t1, 0x06789

    li s0, CHOP_PAIRS
chop_loop:
    gpio_high                      // ===== fase ALU =====
    li s1, CAT_ITERS
cat_phase:
    .rept 16
    addi t0, t0, 1
    xor  t1, t1, t0
    slli t2, t0, 2
    add  t3, t1, t2
    .endr
    addi s1, s1, -1
    bnez s1, cat_phase

    gpio_low                       // ===== fase IDLE (core dormido) =====
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
