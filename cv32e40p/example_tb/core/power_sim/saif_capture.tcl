# XSim: captura SAIF del core durante el bucle dominado en regimen estable.
# Reloj del TB = 10 MHz (100 ns/ciclo). Warmup 30 us (pasa reset + entra al
# bucle), ventana de 200 us (~2000 ciclos, promedio de conmutacion estable).
# Tiempos escalados x10 respecto a la version 100 MHz para cubrir los mismos
# ~2000 ciclos -> mismos toggle COUNTS pero sobre 10x el tiempo => densidad /10.
# La instancia del core es tb_top/wrapper_i/wrapper_i/core_i.
run 30 us
open_saif core.saif
log_saif [get_objects -r /tb_top/wrapper_i/wrapper_i/core_i/*]
run 200 us
close_saif
quit
