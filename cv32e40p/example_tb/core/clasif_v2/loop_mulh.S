# Bucle dominado: MULH (multiplicador MAC, FSM ~4 ciclos). 64 mulh* por
# iteración, mezclando las tres variantes.
# void loop_body(iters a0, opa a1, opb a2)
  .text
  .option norvc
  .globl loop_body
loop_body:
  mv     t0, a1
  mv     t1, a2
1:
  .rept 16
  mulh   t2, t0, t1
  mulhu  t3, t0, t1
  mulhsu t4, t0, t1
  mulh   t5, t2, t1
  .endr
  addi a0, a0, -1
  bnez a0, 1b
  ret
