/* csr_test.S — test minimo de contadores CSR para CV32E40P en FPGA
 * No usa runtime ni UART. GDB lee resultados en registros a0-a5.
 * Compilar: riscv32-unknown-elf-gcc -nostdlib -march=rv32imc -mabi=ilp32 -T csr_test.ld csr_test.S -o csr_test.elf
 */

.section .text
.globl _start
_start:
    /* Configura mtvec a trap_handler para no caer en 0x0 */
    la   t0, trap_handler
    csrw mtvec, t0

    /* Stack en L2 SRAM */
    li   sp, 0x1c010000

    /* Reset de los 6 contadores CSR */
    csrw 0xBC0, zero   /* ARITH  */
    csrw 0xBC1, zero   /* LOGIC  */
    csrw 0xBC2, zero   /* MEMORY */
    csrw 0xBC3, zero   /* BRANCH */
    csrw 0xBC4, zero   /* JUMP   */
    csrw 0xBC5, zero   /* FLOAT  */

    /* == Instrucciones ARITMETICAS (10x ADD) == */
    li   t1, 1
    li   t2, 2
    add  t3, t1, t2
    add  t3, t3, t1
    add  t3, t3, t2
    add  t3, t3, t1
    add  t3, t3, t2
    add  t3, t3, t1
    add  t3, t3, t2
    add  t3, t3, t1

    /* == Instrucciones LOGICAS (4x AND/OR) == */
    and  t4, t1, t2
    and  t4, t3, t2
    or   t4, t1, t2
    or   t4, t3, t1

    /* == Instrucciones MEMORY (2x SW + 2x LW) == */
    li   t5, 0x1c00f000
    sw   t3, 0(t5)
    sw   t4, 4(t5)
    lw   t6, 0(t5)
    lw   t6, 4(t5)

    /* Leer contadores -> a0..a5 (los lee GDB) */
    csrr a0, 0xBC0   /* ARITH  */
    csrr a1, 0xBC1   /* LOGIC  */
    csrr a2, 0xBC2   /* MEMORY */
    csrr a3, 0xBC3   /* BRANCH */
    csrr a4, 0xBC4   /* JUMP   */
    csrr a5, 0xBC5   /* FLOAT  */

    ebreak

trap_handler:
    ebreak
