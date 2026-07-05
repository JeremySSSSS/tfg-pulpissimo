# Chopper — medición diferencial de potencia por categoría (física, sin tocar la placa)

Mide la potencia dinámica de cada categoría **restando idle**, pero alternando
RÁPIDO (cada ~0.3 s) entre categoría e idle. Como las fases adyacentes están a
<1 s, la **deriva térmica (lenta) se cancela** y la señal de ~10 mW queda
resoluble (técnica chopper / lock-in). Se mide el mismo riel +5 V de siempre.

## Idea
```
GPIO8:  alto(0.3s) bajo(0.3s) alto(0.3s) bajo(0.3s) ... ×500   (~5 min)
        [categoría] [ idle  ] [categoría] [ idle  ]
ESP32:  bina la potencia por estado del GPIO -> promedio_alto y promedio_bajo
        DELTA = promedio_alto - promedio_bajo = dinámica de la categoría
```

## Componentes
- `chopper.S` (+ `platform.inc`, `link.ld`): firmware RISC-V que alterna. Un .elf
  por categoría (`make all`). CAT_ITERS por categoría para fases de ~0.3 s.
- `chopper_read.ino` (en `TTGO LORA32/chopper_read/`): firmware ESP32 que bina por
  fase y sube el DELTA al Sheet. **Hay que flashearlo.**
- `run_chopper.py`: corre cada chopper por JTAG y lee el delta del Sheet.

## Uso
```bash
# 1) compilar los chopper
make all

# 2) flashear el ESP32 con el firmware chopper (UNA vez)
arduino-cli compile --fqbn esp32:esp32:esp32 -u -p /dev/ttyACM0 \
    "/home/jjsotoch/pulp/tfg-pulpissimo/TTGO LORA32/chopper_read"

# 3) con OpenOCD en :3333, capturar (cada categoría ~5 min)
python3 run_chopper.py alu mul mulh div mem ctrl float
#  -> chopper_results.csv con la potencia dinámica [mW] por categoría
```

## Por qué puede funcionar donde la resta normal (M1) falló
M1 restaba P_categoría y P_idle medidos con MINUTOS de diferencia -> la deriva
(~10-15 mW) entre ambos arruinaba la resta. Acá se restan fases a <1 s -> la
deriva es despreciable. Números: señal ~10 mW, ruido por par ~0.7 mW, 500 pares
-> ruido final ~0.03 mW (señal ~300× sobre el ruido).

## Es un EXPERIMENTO
Hay que tunear: duración de fase (END_GAP_MS, CAT_ITERS), nº de pares, y descarte
de muestras de transición (SKIP_AFTER_EDGE). El resultado depende de la estabilidad
de la medición rápida del ESP32. Validar contra la simulación (alu~7.5/div~3.7 mW a
10 MHz).
