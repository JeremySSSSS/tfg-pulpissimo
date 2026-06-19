// M1 - bucle dominado FLOAT.  ~5 min a 10 MHz (9M iter x 256 instr/iter).
// 256 fadd/fmul/fsub/fmax INDEPENDIENTES (operandos ft0/ft1 fijos, sin cadena
// serial ni fmadd -> pipelinean ~1.3 cic/op) por iteracion + addi/bnez.
// Requiere -march=rv32imfc. Vuelca 16 CSR + mcycle a 'results'.
#include "platform.inc"

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
    csrci 0x320, 1                  // habilita mcycle

    li t0, 0x6000                   // marca estado FP como inicializado
    csrs mstatus, t0
    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)

    reset_category_counters
    li s0, 9000000                  // LOOP_COUNT

    gpio_high

    csrr s1, mcycle
measurement_loop:
    .rept 64
    fadd.s ft2, ft0, ft1
    fmul.s ft3, ft0, ft1
    fsub.s ft4, ft1, ft0
    fmax.s ft5, ft2, ft3
    .endr
    addi s0, s0, -1
    bnez s0, measurement_loop
    csrr s2, mcycle

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
