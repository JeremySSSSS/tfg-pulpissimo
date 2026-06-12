# Bucles dominados por categoría

Firmware bare-metal para caracterizar potencia en PULPissimo/CV32E40P sobre
Nexys A7. Cada ELF ejecuta 64 instrucciones objetivo por iteración y solamente
dos instrucciones de control (`addi` y `bnez`), por lo que la categoría objetivo
representa aproximadamente el 97 % del bloque dinámico. La rutina de branch es
prácticamente 100 % branch.

## Compilación

```bash
cd /home/jjsotoch/pulp/tfg-power/firmware/dominated_loops
make
```

Se generan:

- `arith.elf`
- `logic.elf`
- `memory.elf`
- `branch.elf`
- `jump.elf`
- `float.elf`
- `frequency_probe.elf`

La duración se ajusta en compilación:

```bash
make clean
make LOOP_COUNT=4000000
```

## Ejecución con GDB

```gdb
target remote :3333
monitor reset halt
load arith.elf
set $pc = _start
continue
```

El flanco ascendente de GPIO8 inicia la ventana de medición y el descendente la
termina. Al final se ejecuta `ebreak`. GPIO8 debe estar conectado a GPIO26 de la
ESP32 y ambas tarjetas deben compartir GND.

Los resultados se consultan con:

```gdb
x/14uw &results
```

Orden:

1. Arithmetic low/high
2. Logic low/high
3. Memory low/high
4. Branch low/high
5. Jump low/high
6. Floating point low/high
7. `mcycle` inicial/final

Los dos accesos MMIO que levantan y bajan GPIO8 añaden aproximadamente dos
instrucciones a la categoría Memory. Su efecto es despreciable para ventanas
largas, pero debe documentarse o restarse al procesar los conteos.

## Verificación de frecuencia

La entrada de la Nexys A7 es de 100 MHz, pero el IP y el bitstream actuales no entregan esa frecuencia directamente al core. Los archivos generados y el reporte de temporización confirman:

- entrada `sys_clk`: 100 MHz (periodo de 10 ns);
- salida `clk_out1`/reloj del SoC: 10 MHz (periodo de 100 ns);
- salida `clk_out2`/reloj periférico: 5 MHz (periodo de 200 ns).

El script del generador conserva valores por defecto de 100/50 MHz, pero el IP `.xci` existente fue generado con 10/5 MHz. Para el experimento debe registrarse 10 MHz mientras se utilice este bitstream.

Esto demuestra la frecuencia configurada, pero la comprobación física se hace
con `frequency_probe.elf`. Por defecto cambia el LED `led1_o` de la Nexys A7 (pin K15, `pad_io09`)
cada 5 000 000 ciclos de `mcycle`. Si el core está a 10 MHz:

- semiperiodo medido: 0.5 s;
- periodo completo medido: 1.0 s;
- frecuencia de parpadeo del LED: 1 Hz.

La frecuencia del core se calcula como:

```text
f_core = (2 * HALF_PERIOD_CYCLES) / periodo_LED
```

Por ejemplo, con 5 000 000 ciclos y un periodo medido de 1.000 s, el resultado
es 10 MHz.
