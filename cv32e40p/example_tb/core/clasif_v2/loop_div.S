# Bucle dominado: DIV (divisor serial, 4-32 ciclos según operandos).
# 64 div/divu/rem/remu por iteración con los operandos que pasa el harness
# (DIV_MIN / DIV_MAX / aleatorios) — la base del experimento de constancia
# de p_div: las tres variantes deben dar el mismo DIV_CYC/ciclo de trabajo.
# void loop_body(iters a0, opa a1=dividendo, opb a2=divisor)
  .text
  .option norvc
  .globl loop_body
loop_body:
1:
  .rept 16
  div  t0, a1, a2
  divu t1, a1, a2
  rem  t2, a1, a2
  remu t3, a1, a2
  .endr
  addi a0, a0, -1
  bnez a0, 1b
  ret
