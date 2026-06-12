# Bucle dominado: CTRL (flush/refetch). 64 saltos incondicionales por
# iteración (j = jal x0); el bnez de control tomado también suma a CTRL,
# así que la dominancia de este bucle es ~100 %.
# void loop_body(iters a0, opa a1, opb a2)
  .text
  .option norvc
  .globl loop_body
loop_body:
1:
  .rept 64
  j    . + 4
  .endr
  addi a0, a0, -1
  bnez a0, 1b
  ret
