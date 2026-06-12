# Bucle dominado: MUL (multiplicador MAC, 1 ciclo). 64 mul por iteración.
# void loop_body(iters a0, opa a1, opb a2)
  .text
  .option norvc
  .globl loop_body
loop_body:
  mv   t0, a1
  mv   t1, a2
1:
  .rept 16
  mul  t2, t0, t1
  mul  t3, t2, t0
  mul  t4, t3, t1
  mul  t5, t4, t0
  .endr
  addi a0, a0, -1
  bnez a0, 1b
  ret
