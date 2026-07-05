# Sintesis OOC (out-of-context) del CV32E40P solo, para analisis de potencia.
# FPU=0 (etapa 1: 6 categorias enteras). Reusa el flist del core + los paquetes
# externos (cf_math, fpnew_pkg) igual que el flujo XSim de verificacion.
#
# Uso:  vivado -mode batch -source synth_core.tcl
# Salida: core_synth.dcp (checkpoint para read_saif + report_power)

set CORE_ROOT [file normalize [file join [pwd] .. .. ..]]
# (este script se corre desde example_tb/core/power_sim/)
if {![file exists $CORE_ROOT/cv32e40p_manifest.flist]} {
    set CORE_ROOT /home/jjsotoch/pulp/tfg-pulpissimo/cv32e40p
}
set RTL    $CORE_ROOT/rtl
set FPNEW  [lindex [glob /home/jjsotoch/pulp/pulpissimo/.bender/git/checkouts/fpnew-*/src] 0]
set CFMATH [lindex [glob /home/jjsotoch/pulp/pulpissimo/.bender/git/checkouts/common_cells-*/src/cf_math_pkg.sv] 0]
set PART   xc7a100tcsg324-1

set incdirs [list $RTL/include $CORE_ROOT/bhv $CORE_ROOT/bhv/include $CORE_ROOT/sva]

puts ">>> CORE_ROOT = $CORE_ROOT"
puts ">>> FPNEW     = $FPNEW"
puts ">>> CFMATH    = $CFMATH"

# Paquetes externos primero (orden de compilacion).
read_verilog -sv $CFMATH
read_verilog -sv $FPNEW/fpnew_pkg.sv

# Archivos del core desde el flist (sustituye DESIGN_RTL_DIR, salta comentarios,
# +incdir y el cv32e40p_fpu_pkg.sv que upstream borro -> lo cubre fpnew_pkg).
set fh [open $CORE_ROOT/cv32e40p_manifest.flist r]
set data [read $fh]
close $fh
foreach line [split $data "\n"] {
    set line [string trim $line]
    if {$line eq ""} continue
    if {[string match "//*" $line]} continue
    if {[string match "+incdir*" $line]} continue
    if {[string match "*cv32e40p_fpu_pkg*" $line]} continue
    regsub -all {\$\{DESIGN_RTL_DIR\}} $line $RTL line
    set line [file normalize $line]
    if {![file exists $line]} { puts "AVISO: no existe $line (salto)"; continue }
    read_verilog -sv $line
}

puts ">>> Sintetizando cv32e40p_core OOC (FPU=0)..."
synth_design -top cv32e40p_core -part $PART -mode out_of_context \
    -generic FPU=0 -include_dirs $incdirs

write_checkpoint -force core_synth.dcp
report_utilization -file util_core.rpt
puts ">>> Listo: core_synth.dcp + util_core.rpt"
