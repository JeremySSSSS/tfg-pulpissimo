#include "platform.inc"

#ifndef LOOP_COUNT
#define LOOP_COUNT 2000000
#endif

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


    reset_category_counters
    li s0, LOOP_COUNT

    /* The GPIO edge defines the measured interval. The two marker stores are
       therefore visible as a negligible +2 contribution to MEMORY. */
    gpio_high
    csrr s1, mcycle

measurement_loop:



    .rept 32
        beq  zero, zero, 1f
1:
        bne  zero, zero, 2f
2:
    .endr



    addi s0, s0, -1
    bnez s0, measurement_loop

    csrr s2, mcycle
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

.align 4
float_words:
    .word 0x3f800000, 0x40000000
