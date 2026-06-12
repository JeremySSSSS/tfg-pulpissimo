# Bucle dominado: MEM (LSU + TCDM). 64 accesos por iteración (32 sw + 32 lw)
# sobre el buffer que pasa el harness.
# void loop_body(iters a0, opa a1=&buf, opb a2=dato)
  .text
  .option norvc
  .globl loop_body
loop_body:
1:
  .rept 8
  sw   a2, 0(a1)
  sw   a2, 4(a1)
  sw   a2, 8(a1)
  sw   a2, 12(a1)
  lw   t0, 0(a1)
  lw   t1, 4(a1)
  lw   t2, 8(a1)
  lw   t3, 12(a1)
  .endr
  addi a0, a0, -1
  bnez a0, 1b
  ret
