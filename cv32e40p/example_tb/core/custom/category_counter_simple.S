.section .text
.global main
.type main, @function

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

arith_block_start:
    addi t0, zero, 9
    addi t1, zero, 4
    add  t2, t0, t1
    sub  t3, t2, t1
    mul  t4, t0, t1
    addi t5, t4, 1
    add  t6, t5, t3
    sub  t2, t6, t0
    mul  t3, t2, t1
    addi t4, t3, 2
arith_block_end:

logic_block_start:
    and  t2, t0, t1
    or   t3, t2, t0
    xor  t4, t3, t1
    slli t5, t4, 1
    srli t6, t5, 1
    and  t2, t6, t4
    or   t3, t2, t5
    xor  t4, t3, t6
    slli t5, t4, 2
    srli t6, t5, 2
logic_block_end:

memory_block_start:
    la   t0, data_words
    lw   t1, 0(t0)
    lw   t2, 4(t0)
    sw   t1, 8(t0)
    sw   t2, 12(t0)
    lw   t3, 8(t0)
    lw   t4, 12(t0)
    sw   t3, 16(t0)
    sw   t4, 20(t0)
memory_block_end:

branch_block_start:
    addi t0, zero, 3
    addi t1, zero, 3
    beq  t0, t1, branch_1
    addi t2, zero, 99
branch_1:
    bne  t0, t1, branch_2
branch_2:
    beq  t0, t1, branch_3
    addi t2, zero, 88
branch_3:
    bne  t0, t1, branch_4
branch_4:
    beq  t0, t1, branch_5
    addi t2, zero, 77
branch_5:
    bne  t0, t1, branch_6
branch_6:
branch_block_end:

jump_block_start:
    jal  t0, jump_1
    addi t1, zero, 66
jump_1:
    jal  t0, jump_2
    addi t1, zero, 55
jump_2:
    jal  t0, jump_3
    addi t1, zero, 44
jump_3:
    jal  t0, jump_4
    addi t1, zero, 33
jump_4:
jump_block_end:

read_counters:
    csrr a1, CSR_CAT_ARITH
    csrr a2, CSR_CAT_LOGIC
    csrr a3, CSR_CAT_MEMORY
    csrr a4, CSR_CAT_BRANCH
    csrr a5, CSR_CAT_JUMP
    csrr a6, CSR_CAT_FLOAT

exit_success:
    li   t0, EXIT_REG
    sw   zero, 0(t0)
    wfi

    .option pop

.size main, .-main

.section .data
.align 2
data_words:
    .word 0x11111111
    .word 0x22222222
    .word 0x00000000
    .word 0x00000000
    .word 0x00000000
    .word 0x00000000
