# Breakpoint para el modo GUI: pausa la simulación al final de la región
# medida del clasif_smoke (div=6 && mem=8 && ctrl=5, literales en binario
# porque add_condition de XSim los interpreta así). Vos controlás todo lo
# demás: agregar ondas y darle run.
#
# El "run 100 ns" inicial es necesario: en t=0 las señales están en X y
# cualquier condición dispararía en falso.

set CL /tb_top/wrapper_i/wrapper_i/core_i/insn_classifier_i

run 100 ns

add_condition "$CL/div_q == 110 && $CL/mem_q == 1000 && $CL/ctrl_q == 101" {
  puts "== BREAK: fin de la región medida (contadores con valores finales) =="
  stop
}
