// M1 - bucle dominado CTRL.  ~20 s a 10 MHz (580k iter x ~126 instr retiradas).
// Redisenado para ser REPRESENTATIVO del control de codigo real (antes: 256
// 'j .+4', el caso degenerado: salto incondicional al vecino, sin comparacion,
// sin instrucciones victima -> subestimaba el costo real y discrepaba ~3x con
// la regresion). Misma filosofia que el bucle de division: cubrir el caso real
// variando lo que el costo depende.
//   - branches CONDICIONALES siempre tomados (comparan en la ALU + vacian el
//     pipeline, 3 ciclos) con OPERANDOS QUE CAMBIAN cada iteracion;
//   - distancias de salto variadas (+8, +12) y un jal;
//   - instrucciones VICTIMA tras cada salto: se buscan/decodifican y se
//     descartan sin retirarse (energia de fetch perdida, como en codigo real;
//     NO cuentan en los contadores: solo se retira el flujo de saltos).
// Dominancia: por iteracion se retiran 121 ctrl (120 tomados + bnez) frente a
// 5 ALU (4 updates + addi) -> 96 %. Ventana = flanco de GPIO8 (-> ESP32).
// Vuelca 16 CSR + mcycle a 'results'.
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
    li s0, 580000                   // LOOP_COUNT

    gpio_high

    // operandos de los branches: relaciones invariantes, valores cambiantes.
    // DESPUES de gpio_high: el macro pisa t0/t1 (direccion del GPIO + mascara);
    // inicializarlos antes deja bgeu nunca-tomado y arruina la dominancia.
    li t0, 0x100                    // par     (t1 = t0+1 siempre)
    li t1, 0x101                    // impar   -> bne/bgeu garantizados
    li t2, 0x80001111               // negativo (bit 31 fijo via xori)
    li t3, 0x00000F0F               // positivo pequeno -> blt garantizado

    csrr s1, mcycle
measurement_loop:
    // los operandos avanzan: el comparador de la ALU y las direcciones
    // conmutan con datos distintos en cada pasada (4 instr ALU, ~4 %)
    addi t0, t0, 2                  // sigue par
    addi t1, t1, 2                  // sigue impar (= t0+1)
    addi t3, t3, 2                  // sigue positivo (crece acotado)
    xori t2, t2, 0x5A5              // sigue negativo (bit 31 intacto)
    .rept 24
    bne  t0, t1, 1f                 // tomado (+8): salta 1 victima
    xor  a0, t0, t1                 //   victima: se busca, no se retira
1:  blt  t2, t3, 2f                 // tomado (+12): salta 2 victimas
    add  a1, t2, t3
    sub  a2, t3, t2
2:  bgeu t1, t0, 3f                 // tomado (+8): t1 > t0 sin signo
    and  a3, t0, t2
3:  j    4f                         // jal (+8): salto incondicional real
    or   a4, t1, t3
4:  bne  t3, t2, 5f                 // tomado (+8)
    xor  a5, t2, t3
5:
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
