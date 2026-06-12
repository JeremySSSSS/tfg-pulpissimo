# Ondas + parada automática para inspeccionar el clasificador v2.
# La simulación se detiene sola en el primer csrr a un CSR del clasificador
# (la lectura final del test): en ese instante los 8 contadores muestran los
# valores de la región medida (los mismos que imprime la línea CLASIF).

set CL /tb_top/wrapper_i/wrapper_i/core_i/insn_classifier_i

# add_wave solo existe en modo GUI; en batch se ignora
catch {
  add_wave -radix unsigned $CL/alu_q $CL/mul_q $CL/mulh_q $CL/div_q \
    $CL/mem_q $CL/ctrl_q $CL/float_q $CL/divcyc_q
  add_wave $CL/retire_i $CL/count_en $CL/branch_i $CL/branch_taken_i \
    $CL/branch_q1 $CL/csr_access_i $CL/system_i $CL/alu_operator_i \
    $CL/csr_addr_i
}

# Avanzar más allá del arranque: en t=0 las señales están en X y la
# condición dispararía en falso. A los 100 ns el reset ya definió todo.
run 100 ns

# Parada sobre señales REGISTRADAS (las combinacionales tipo csr_hit/csr_op
# producen disparos falsos por glitches entre instrucciones). La combinación
# div=6 && mem=8 && ctrl=5 solo ocurre al final de la región medida del
# clasif_smoke (justo después del último jal, antes de la lectura).
# Nota: add_condition de XSim interpreta los literales como BINARIO:
# 110=6, 1000=8, 101=5
add_condition "$CL/div_q == 110 && $CL/mem_q == 1000 && $CL/ctrl_q == 101" {
    puts "== Detenido en la lectura de contadores (region medida) =="
    puts "  ALU     = [get_value -radix unsigned $CL/alu_q]"
    puts "  MUL     = [get_value -radix unsigned $CL/mul_q]"
    puts "  MULH    = [get_value -radix unsigned $CL/mulh_q]"
    puts "  DIV     = [get_value -radix unsigned $CL/div_q]"
    puts "  MEM     = [get_value -radix unsigned $CL/mem_q]"
    puts "  CTRL    = [get_value -radix unsigned $CL/ctrl_q]"
    puts "  FLOAT   = [get_value -radix unsigned $CL/float_q]"
    puts "  DIV_CYC = [get_value -radix unsigned $CL/divcyc_q]"
    stop
  }

run all
