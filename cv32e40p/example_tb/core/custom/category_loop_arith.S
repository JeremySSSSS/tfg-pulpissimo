.section .text
.global main
.type main, @function

#ifndef LOOP_OUTER
#define LOOP_OUTER 1000
#endif
#ifndef LOOP_INNER
#define LOOP_INNER 1200000
#endif

.equ EXIT_REG,          0x20000004
.equ CSR_CAT_ARITH,     0xBC0
.equ CSR_CAT_ARITH_HI,  0xBC1
.equ CSR_CAT_LOGIC,     0xBC2
.equ CSR_CAT_LOGIC_HI,  0xBC3
.equ CSR_CAT_MEMORY,    0xBC4
.equ CSR_CAT_MEMORY_HI, 0xBC5
.equ CSR_CAT_BRANCH,    0xBC6
.equ CSR_CAT_BRANCH_HI, 0xBC7
.equ CSR_CAT_JUMP,      0xBC8
.equ CSR_CAT_JUMP_HI,   0xBC9
.equ CSR_CAT_FLOAT,     0xBCA
.equ CSR_CAT_FLOAT_HI,  0xBCB

.macro reset_counters
    csrw CSR_CAT_LOGIC, zero
    csrw CSR_CAT_LOGIC_HI, zero
    csrw CSR_CAT_MEMORY, zero
    csrw CSR_CAT_MEMORY_HI, zero
    csrw CSR_CAT_BRANCH, zero
    csrw CSR_CAT_BRANCH_HI, zero
    csrw CSR_CAT_JUMP, zero
    csrw CSR_CAT_JUMP_HI, zero
    csrw CSR_CAT_FLOAT, zero
    csrw CSR_CAT_FLOAT_HI, zero
    csrw CSR_CAT_ARITH, zero
    csrw CSR_CAT_ARITH_HI, zero
.endm
main:
    .option push
    .option norvc

    li   s0, LOOP_OUTER
    reset_counters

outer_loop:
    li   s1, LOOP_INNER
arith_loop:
    add  t2, t0, t1
    sub  t3, t2, t1
    addi t4, t3, 1
    add  t5, t4, t2
    sub  t6, t5, t0
    addi t0, t6, 2
    add  t1, t0, t4
    sub  t2, t1, t3
    addi s1, s1, -1
    bnez s1, arith_loop
    addi s0, s0, -1
    bnez s0, outer_loop

read_counters:
    csrr a0, CSR_CAT_ARITH
    csrr a1, CSR_CAT_ARITH_HI
    csrr a2, CSR_CAT_LOGIC
    csrr a3, CSR_CAT_MEMORY
    csrr a4, CSR_CAT_BRANCH
    csrr a5, CSR_CAT_JUMP

    li   t0, EXIT_REG
    sw   zero, 0(t0)
    wfi

    .option pop
.size main, .-main
