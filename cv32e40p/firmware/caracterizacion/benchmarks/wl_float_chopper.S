#ifndef CHOP_PAIRS
#define CHOP_PAIRS 50
#endif
#ifndef CAT_ITERS
#define CAT_ITERS 35700
#endif
#ifndef IDLE_TICKS
#define IDLE_TICKS 3000000
#endif

#include "/home/jjsotoch/pulp/tfg-pulpissimo/cv32e40p/firmware/caracterizacion/metodo2_chopper/fuentes/platform.inc"

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

    li t0, 0x6000
    csrs mstatus, t0
    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)

    reset_category_counters
    li s0, CHOP_PAIRS
chop_loop:
    gpio_high
    li s1, CAT_ITERS
cat_phase:
    .rept 16
    fadd.s ft2, ft0, ft1
    fmul.s ft3, ft0, ft1
    fsub.s ft4, ft1, ft0
    fmax.s ft5, ft2, ft3
    .endr
    addi s1, s1, -1
    bnez s1, cat_phase

    gpio_low
    wfi_idle IDLE_TICKS

    addi s0, s0, -1
    bnez s0, chop_loop

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
float_words:
    .word 0x3f800000, 0x40000000

.section .bss
.align 4
.globl results
results:
    .space 72
