#include "platform.inc"

#ifndef LOOP_COUNT
#define LOOP_COUNT 2000000
#endif

#if !defined(CATEGORY_ARITH) && !defined(CATEGORY_LOGIC) && \
    !defined(CATEGORY_MEMORY) && !defined(CATEGORY_BRANCH) && \
    !defined(CATEGORY_JUMP) && !defined(CATEGORY_FLOAT)
#error "Define exactly one CATEGORY_* macro"
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

#ifdef CATEGORY_MEMORY
    la s2, data_words
#endif
#ifdef CATEGORY_FLOAT
    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)
#endif

    reset_category_counters
    li s0, LOOP_COUNT

    /* The GPIO edge defines the measured interval. The two marker stores are
       therefore visible as a negligible +2 contribution to MEMORY. */
    gpio_high
    csrr s1, mcycle

measurement_loop:
#ifdef CATEGORY_ARITH
    .rept 8
        add  t2, t2, t3
        sub  t3, t2, t4
        addi t4, t4, 3
        add  t5, t5, t2
        mul  t6, t2, t4
        add  a4, t6, t3
        sub  a5, a4, t2
        addi a6, a5, 7
    .endr
#endif

#ifdef CATEGORY_LOGIC
    .rept 8
        xor  t2, t2, t3
        or   t3, t2, t4
        and  t4, t3, t5
        slli t5, t4, 1
        srli t6, t5, 1
        xori a4, t6, 0x55
        ori  a5, a4, 0x0f
        andi a6, a5, 0x7f
    .endr
#endif

#ifdef CATEGORY_MEMORY
    .rept 8
        lw t2, 0(s2)
        lw t3, 4(s2)
        sw t2, 8(s2)
        sw t3, 12(s2)
        lw t4, 8(s2)
        lw t5, 12(s2)
        sw t4, 16(s2)
        sw t5, 20(s2)
    .endr
#endif

#ifdef CATEGORY_BRANCH
    .rept 32
        beq  zero, zero, 1f
1:
        bne  zero, zero, 2f
2:
    .endr
#endif

#ifdef CATEGORY_JUMP
    .rept 64
        jal zero, 1f
1:
    .endr
#endif

#ifdef CATEGORY_FLOAT
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
#endif

    addi s0, s0, -1
    bnez s0, measurement_loop

    csrr s2, mcycle
    gpio_low

    /* Read every counter before storing results, so result writes do not
       alter the captured MEMORY value. */
    csrr a0, CSR_CAT_ARITH_LO
    csrr a1, CSR_CAT_ARITH_HI
    csrr a2, CSR_CAT_LOGIC_LO
    csrr a3, CSR_CAT_LOGIC_HI
    csrr a4, CSR_CAT_MEMORY_LO
    csrr a5, CSR_CAT_MEMORY_HI
    csrr a6, CSR_CAT_BRANCH_LO
    csrr a7, CSR_CAT_BRANCH_HI
    csrr t0, CSR_CAT_JUMP_LO
    csrr t1, CSR_CAT_JUMP_HI
    csrr t2, CSR_CAT_FLOAT_LO
    csrr t3, CSR_CAT_FLOAT_HI

    la t4, results
    sw a0,  0(t4)
    sw a1,  4(t4)
    sw a2,  8(t4)
    sw a3, 12(t4)
    sw a4, 16(t4)
    sw a5, 20(t4)
    sw a6, 24(t4)
    sw a7, 28(t4)
    sw t0, 32(t4)
    sw t1, 36(t4)
    sw t2, 40(t4)
    sw t3, 44(t4)
    sw s1, 48(t4)
    sw s2, 52(t4)

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
    .space 56
