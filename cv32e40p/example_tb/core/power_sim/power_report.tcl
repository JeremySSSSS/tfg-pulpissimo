# Vivado: aplica el SAIF (actividad de conmutacion del bucle) al netlist del
# core sintetizado y reporta la potencia dinamica.
#   vivado -mode batch -source power_report.tcl -tclargs <saif> <out.rpt>
# El SAIF tiene los nets bajo tb_top/.../core_i; -strip_path los mapea al
# checkpoint OOC (donde el core es el top).
set saif [lindex $argv 0]
set out  [lindex $argv 1]
open_checkpoint core_synth.dcp
# Define el reloj del core (10 MHz = el del sim y el de la placa) para que
# report_power calcule bien la potencia de clock-tree; sin esto Vivado asume una
# freq por defecto y infla todo. Debe COINCIDIR con la freq de captura del SAIF.
create_clock -name clk -period 100.000 [get_ports clk_i]
read_saif -strip_path tb_top/wrapper_i/wrapper_i/core_i $saif
report_power -file $out
puts ">>> power report: $out"
