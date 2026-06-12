# Bucle dominado: ALU_SIMPLE. 64 ops de ALU por iteración + addi/bnez de
# control (el addi también es ALU; el bnez tomado va a CTRL, el último no
# tomado a ALU). void loop_body(iters a0, opa a1, opb a2)
  .text
  .option norvc
  .globl loop_body
loop_body:
  mv   t0, a1
  mv   t1, a2
1:
  .rept 16
  addi t0, t0, 1
  xor  t1, t1, t0
  slli t2, t0, 2
  add  t3, t1, t2
  .endr
  addi a0, a0, -1
  bnez a0, 1b
  ret
