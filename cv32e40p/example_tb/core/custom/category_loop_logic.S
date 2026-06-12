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
    csrw CSR_CAT_ARITH, zero
    csrw CSR_CAT_ARITH_HI, zero
    csrw CSR_CAT_MEMORY, zero
    csrw CSR_CAT_MEMORY_HI, zero
    csrw CSR_CAT_BRANCH, zero
    csrw CSR_CAT_BRANCH_HI, zero
    csrw CSR_CAT_JUMP, zero
    csrw CSR_CAT_JUMP_HI, zero
    csrw CSR_CAT_FLOAT, zero
    csrw CSR_CAT_FLOAT_HI, zero
    csrw CSR_CAT_LOGIC, zero
    csrw CSR_CAT_LOGIC_HI, zero
.endm
main:
    .option push
    .option norvc

    li   t0, 0x55555555
    li   t1, 0x0f0f0f0f
    li   s0, LOOP_OUTER
    reset_counters

outer_loop:
    li   s1, LOOP_INNER
logic_loop:
    and  t2, t0, t1
    or   t3, t2, t0
    xor  t4, t3, t1
    slli t5, t4, 1
    srli t6, t5, 1
    and  t2, t6, t4
    or   t3, t2, t5
    xor  t4, t3, t6
    addi s1, s1, -1
    bnez s1, logic_loop
    addi s0, s0, -1
    bnez s0, outer_loop

read_counters:
    csrr a0, CSR_CAT_LOGIC
    csrr a1, CSR_CAT_LOGIC_HI
    csrr a2, CSR_CAT_ARITH
    csrr a3, CSR_CAT_MEMORY
    csrr a4, CSR_CAT_BRANCH
    csrr a5, CSR_CAT_JUMP

    li   t0, EXIT_REG
    sw   zero, 0(t0)
    wfi

    .option pop
.size main, .-main
