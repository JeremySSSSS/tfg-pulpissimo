// CHOPPER: medicion diferencial por categoria, fisica, sin tocar la placa.
// Alterna RAPIDO entre una fase CATEGORIA (GPIO8 alto) y una fase IDLE (GPIO8
// bajo), CHOP_PAIRS veces. El ESP32 bina la potencia por estado del GPIO y
// reporta (promedio_alto - promedio_bajo) = potencia dinamica de la categoria
// sobre el idle. Como las fases adyacentes estan a <1 s, la deriva termica
// (lenta) se cancela -> la senal de ~10 mW queda resoluble (lock-in/chopper).
//
// Compilar una vez por categoria con -DCATEGORY_<X>. CAT_ITERS e IDLE_ITERS
// se ajustan (Makefile) para que cada fase dure ~lo mismo (~0.3 s).
#include "platform.inc"

#ifndef CHOP_PAIRS
#define CHOP_PAIRS 500          // pares categoria/idle (cada par ~0.6 s -> ~5 min)
#endif
#ifndef CAT_ITERS
#define CAT_ITERS 44000         // iteraciones de la fase categoria (~0.3 s)
#endif
#ifndef IDLE_ITERS
#define IDLE_ITERS 3000         // iteraciones de la fase idle (~0.3 s con NOPs)
#endif
#ifndef IDLE_NOPS
#define IDLE_NOPS 1000          // NOPs por iteracion (referencia pasiva, saltos raros)
#endif

#if !defined(CATEGORY_ALU)  && !defined(CATEGORY_MUL)  && \
    !defined(CATEGORY_MULH) && !defined(CATEGORY_DIV)  && \
    !defined(CATEGORY_MEM)  && !defined(CATEGORY_CTRL) && !defined(CATEGORY_FLOAT)
#error "Define un CATEGORY_* (ALU/MUL/MULH/DIV/MEM/CTRL/FLOAT)"
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

#ifdef CATEGORY_FLOAT
    li t0, 0x6000
    csrs mstatus, t0
    la t0, float_words
    flw ft0, 0(t0)
    flw ft1, 4(t0)
#endif

    // Operandos de la categoria (una sola vez).
#if defined(CATEGORY_ALU) || defined(CATEGORY_MUL) || defined(CATEGORY_MULH)
    li t0, 0x12345
    li t1, 0x06789
#endif
#ifdef CATEGORY_DIV
    li a1, 0x7FFFFF01
    li a2, 0x000037A1
#endif
#ifdef CATEGORY_MEM
    la s2, data_words
    li a2, 0xABCD1234
#endif

    li s0, CHOP_PAIRS

chop_loop:
    // ===================== FASE CATEGORIA (GPIO alto) =====================
    gpio_high
    li s1, CAT_ITERS
cat_phase:
#ifdef CATEGORY_ALU
    .rept 16
    addi t0, t0, 1
    xor  t1, t1, t0
    slli t2, t0, 2
    add  t3, t1, t2
    .endr
#endif
#ifdef CATEGORY_MUL
    .rept 16
    mul  t2, t0, t1
    mul  t3, t2, t0
    mul  t4, t3, t1
    mul  t5, t4, t0
    .endr
#endif
#ifdef CATEGORY_MULH
    .rept 16
    mulh   t2, t0, t1
    mulhu  t3, t0, t1
    mulhsu t4, t0, t1
    mulh   t5, t2, t1
    .endr
#endif
#ifdef CATEGORY_DIV
    .rept 16
    div  t0, a1, a2
    divu t1, a1, a2
    rem  t2, a1, a2
    remu t3, a1, a2
    .endr
#endif
#ifdef CATEGORY_MEM
    .rept 8
    sw   a2, 0(s2)
    sw   a2, 4(s2)
    sw   a2, 8(s2)
    sw   a2, 12(s2)
    lw   t0, 0(s2)
    lw   t1, 4(s2)
    lw   t2, 8(s2)
    lw   t3, 12(s2)
    .endr
#endif
#ifdef CATEGORY_CTRL
    .rept 64
    j    . + 4
    .endr
#endif
#ifdef CATEGORY_FLOAT
    .rept 16
    fadd.s ft2, ft0, ft1
    fmul.s ft3, ft0, ft1
    fsub.s ft4, ft1, ft0
    fmax.s ft5, ft2, ft3
    .endr
#endif
    addi s1, s1, -1
    bnez s1, cat_phase

    // ======================== FASE IDLE (GPIO bajo) =======================
    // Referencia PASIVA: bloque grande de NOPs (operandos constantes -> minimo
    // toggling de datapath) con saltos RAROS (1 cada IDLE_NOPS -> poco flush).
    // Mucho mas pasivo que un bucle apretado de saltos -> mejor linea base.
    gpio_low
    li s1, IDLE_ITERS
idle_phase:
    .rept IDLE_NOPS
    nop
    .endr
    addi s1, s1, -1
    bnez s1, idle_phase

    addi s0, s0, -1
    bnez s0, chop_loop

    gpio_low
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
    .space 72
