// M1 - linea base IDLE PASIVA.  ~5 min a 10 MHz (3M iter x ~1003 cic/iter).
// Referencia pasiva: bloque de 1000 NOPs (operandos constantes -> no togglean el
// datapath) con saltos RAROS (1 cada 1000 -> sin flush). Mucho mas cerca de la
// estatica pura que un bucle de saltos. Da P_idle (baseline), sin coeficiente.
// Consistente con la fase idle del chopper.
// Ventana de medicion = flanco de GPIO8 (-> ESP32). Vuelca 16 CSR + mcycle a 'results'.
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
    li s0, 3000000                  // LOOP_COUNT (con 1000 NOPs/iter -> ~5 min)

    gpio_high

    csrr s1, mcycle
measurement_loop:
    .rept 1000
    nop
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
