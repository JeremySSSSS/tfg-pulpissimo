#include "platform.inc"

#ifndef HALF_PERIOD_CYCLES
#define HALF_PERIOD_CYCLES 5000000
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
    led_init

    csrci 0x320, 1
    led_high

    li s0, HALF_PERIOD_CYCLES
    li s2, 0
    csrr s1, mcycle

toggle_loop:
    add s1, s1, s0
wait_half_period:
    csrr t2, mcycle
    sub t3, t2, s1
    blt t3, zero, wait_half_period

    xori s2, s2, 1
    beqz s2, drive_low
    led_high
    j toggle_loop

drive_low:
    led_low
    j toggle_loop

trap_handler:
    ebreak
    j trap_handler

    .option pop
.size _start, .-_start
