#include "platform.inc"

#ifndef LOOP_COUNT
#define LOOP_COUNT 100000
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

    /* Enable mcycle and mark floating-point state as initialized. */
    csrci 0x320, 1
    li t0, 0x6000
    csrs mstatus, t0

    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)

    csrw 0xBC0, zero
    csrw 0xBC1, zero
    csrw 0xBC2, zero
    csrw 0xBC3, zero
    csrw 0xBC4, zero
    csrw 0xBC5, zero
    li s0, LOOP_COUNT

    /* The GPIO edge defines the measured interval. The two marker stores are
       therefore visible as a negligible +2 contribution to MEMORY. */
    gpio_high
    csrr s1, mcycle

measurement_loop:





    .rept 8
        fadd.s ft2, ft0, ft1
        fsub.s ft3, ft2, ft1
        fmul.s ft4, ft3, ft0
        fadd.s ft5, ft4, ft2
        fsub.s ft6, ft5, ft3
        fmul.s ft7, ft6, ft1
        fadd.s ft2, ft7, ft4
        fsub.s ft3, ft2, ft0
    .endr

    addi s0, s0, -1
    bnez s0, measurement_loop

    csrr s2, mcycle
    gpio_low

    /* Map used by the currently programmed bitstream: six 32-bit CSRs. */
    csrr a0, 0xBC0
    csrr a1, 0xBC1
    csrr a2, 0xBC2
    csrr a3, 0xBC3
    csrr a4, 0xBC4
    csrr a5, 0xBC5

    la t4, results
    sw a0,  0(t4)
    sw a1,  4(t4)
    sw a2,  8(t4)
    sw a3, 12(t4)
    sw a4, 16(t4)
    sw a5, 20(t4)
    sw s1, 24(t4)
    sw s2, 28(t4)

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

.section .bss
.align 4
.globl results
results:
    .space 32
