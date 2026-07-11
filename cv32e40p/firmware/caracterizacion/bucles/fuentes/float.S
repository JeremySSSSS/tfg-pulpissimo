// M1 - bucle dominado FLOAT.  ~20 s a 10 MHz.
// REDISENADO con operandos VARIADOS (misma leccion que ctrl): la version
// anterior repetia los mismos operandos por siempre y media la cota INFERIOR
// del costo (sin conmutacion de datos; ft0/ft1 eran fijos). Diseno "pool de pares": 10
// registros con valores variados -> 45 pares DISTINTOS de operandos por
// bloque (conmutacion real entre operaciones consecutivas), resultados a un
// registro sumidero (sin realimentacion -> los valores no colapsan), y 2
// updates por iteracion que evolucionan el pool. Dominancia ~98%.
// Operandos inicializados DESPUES de gpio_high (el macro pisa t0/t1).
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

    reset_category_counters
    li s0, 858000                 // LOOP_COUNT

    li t0, 0x6000
    csrs mstatus, t0        // habilita FP
    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)
    flw ft2, 8(t0)
    flw ft3, 12(t0)
    flw ft4, 16(t0)
    flw ft5, 20(t0)
    flw ft6, 24(t0)
    flw ft7, 28(t0)
    flw ft8, 32(t0)
    flw ft9, 36(t0)

    gpio_high

    csrr s1, mcycle
measurement_loop:
    .rept 4
    fadd.s ft10, ft0, ft1
    fmul.s ft10, ft0, ft2
    fsub.s ft10, ft0, ft3
    fadd.s ft10, ft0, ft4
    fmul.s ft10, ft0, ft5
    fsub.s ft10, ft0, ft6
    fadd.s ft10, ft0, ft7
    fmul.s ft10, ft0, ft8
    fsub.s ft10, ft0, ft9
    fadd.s ft10, ft1, ft2
    fmul.s ft10, ft1, ft3
    fsub.s ft10, ft1, ft4
    fadd.s ft10, ft1, ft5
    fmul.s ft10, ft1, ft6
    fsub.s ft10, ft1, ft7
    fadd.s ft10, ft1, ft8
    fmul.s ft10, ft1, ft9
    fsub.s ft10, ft2, ft3
    fadd.s ft10, ft2, ft4
    fmul.s ft10, ft2, ft5
    fsub.s ft10, ft2, ft6
    fadd.s ft10, ft2, ft7
    fmul.s ft10, ft2, ft8
    fsub.s ft10, ft2, ft9
    fadd.s ft10, ft3, ft4
    fmul.s ft10, ft3, ft5
    fsub.s ft10, ft3, ft6
    fadd.s ft10, ft3, ft7
    fmul.s ft10, ft3, ft8
    fsub.s ft10, ft3, ft9
    fadd.s ft10, ft4, ft5
    fmul.s ft10, ft4, ft6
    fsub.s ft10, ft4, ft7
    fadd.s ft10, ft4, ft8
    fmul.s ft10, ft4, ft9
    fsub.s ft10, ft5, ft6
    fadd.s ft10, ft5, ft7
    fmul.s ft10, ft5, ft8
    fsub.s ft10, ft5, ft9
    fadd.s ft10, ft6, ft7
    fmul.s ft10, ft6, ft8
    fsub.s ft10, ft6, ft9
    fadd.s ft10, ft7, ft8
    fmul.s ft10, ft7, ft9
    fsub.s ft10, ft8, ft9
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

.section .bss
.align 4
.globl results
results:
    .space 72
.section .data
.align 4
float_words:
    .float 1.1234567
    .float 1.7654321
    .float 1.3141593
    .float 1.9182736
    .float 1.5556667
    .float 1.2468013
    .float 1.8642097
    .float 1.4321987
    .float 1.6789012
    .float 1.0987654
