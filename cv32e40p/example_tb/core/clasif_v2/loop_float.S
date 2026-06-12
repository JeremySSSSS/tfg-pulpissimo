# Bucle dominado: FLOAT (FPU vía APU). 64 ops de cómputo FP por iteración.
# OJO: requiere elaborar el testbench con FPU=1 (hoy elabora con FPU=0 y
# estas instrucciones serían illegal). En la FPGA la FPU está confirmada.
# Compilar con -march=rv32imfc -mabi=ilp32f; el harness habilita mstatus.FS.
# void loop_body(iters a0, opa a1, opb a2)
  .text
  .option norvc
  .globl loop_body
loop_body:
  fmv.w.x  ft0, a1
  fmv.w.x  ft1, a2
1:
  .rept 16
  fadd.s   ft2, ft0, ft1
  fmul.s   ft3, ft0, ft1
  fsub.s   ft4, ft1, ft0
  fmax.s   ft5, ft2, ft3
  .endr
  addi a0, a0, -1
  bnez a0, 1b
  ret
