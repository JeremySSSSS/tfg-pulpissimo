.section .text
.global main
.type main, @function

.equ STDOUT_REG,      0x10000000
.equ EXIT_REG,        0x20000004
.equ CSR_CAT_ARITH,   0xBC0
.equ CSR_CAT_ARITH_HI,0xBC1
.equ CSR_CAT_LOGIC,   0xBC2
.equ CSR_CAT_LOGIC_HI,0xBC3
.equ CSR_CAT_MEMORY,  0xBC4
.equ CSR_CAT_MEMORY_HI,0xBC5
.equ CSR_CAT_BRANCH,  0xBC6
.equ CSR_CAT_BRANCH_HI,0xBC7
.equ CSR_CAT_JUMP,    0xBC8
.equ CSR_CAT_JUMP_HI, 0xBC9
.equ CSR_CAT_FLOAT,   0xBCA
.equ CSR_CAT_FLOAT_HI,0xBCB

main:
    .option push
    .option norvc

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

    addi t0, zero, 9
    addi t1, zero, 4
    add  t2, t0, t1
    sub  t2, t2, t1
    mul  t2, t0, t1

    csrr t3, CSR_CAT_ARITH
    addi t4, zero, 5
    bne  t3, t4, fail_arith

    csrr t5, CSR_CAT_LOGIC
    bne  t5, zero, fail_logic

    la   a0, pass_msg
    jal  ra, putstr
    addi a0, zero, 0
    jal  zero, exit_direct

fail_arith:
    la   a0, fail_arith_msg
    jal  ra, putstr
    addi a0, zero, 1
    jal  zero, exit_direct

fail_logic:
    la   a0, fail_logic_msg
    jal  ra, putstr
    addi a0, zero, 1
    jal  zero, exit_direct

exit_direct:
    li   t0, EXIT_REG
    sw   a0, 0(t0)
    wfi
    jal  zero, exit_direct

putstr:
    li   t0, STDOUT_REG
1:
    lbu  t1, 0(a0)
    beq  t1, zero, 2f
    sw   t1, 0(t0)
    addi a0, a0, 1
    jal  zero, 1b
2:
    ret

    .option pop

.size main, .-main

.section .rodata
pass_msg:
    .asciz "ASM CATEGORY TEST PASS\n"
fail_arith_msg:
    .asciz "ASM CATEGORY TEST FAIL arith\n"
fail_logic_msg:
    .asciz "ASM CATEGORY TEST FAIL logic\n"
