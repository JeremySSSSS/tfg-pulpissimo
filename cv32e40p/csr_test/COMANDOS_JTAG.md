# Comandos JTAG — CV32E40P en PULPissimo / Nexys A7

## Estado actual
- El clasificador de instrucciones expone 12 CSR de 64 bits: `BC0` a `BCB`.
- `BC0/BC1` = `ARITH`, `BC2/BC3` = `LOGIC`, `BC4/BC5` = `MEMORY`, `BC6/BC7` = `BRANCH`, `BC8/BC9` = `JUMP`, `BCA/BCB` = `FLOAT`.
- El bitstream nuevo quedó en la SD como `xilinx_pulpissimo.bit`.

## Setup previo
### Liberar FT232H si da `LIBUSB_ERROR_BUSY`
```bash
sudo bash -c 'for d in /sys/bus/usb/devices/*; do
  [ -f "$d/idVendor" ] && [ "$(cat "$d/idVendor")" = "0403" ] && [ "$(cat "$d/idProduct")" = "6014" ] && \
  echo "${d##*/}:1.0" > /sys/bus/usb/drivers/ftdi_sio/unbind 2>/dev/null && echo "OK liberado"
done'
```

### Matar OpenOCD colgado
```bash
ps aux | grep openocd
sudo kill -9 <PID>
```

## Debug manual de una prueba
### Terminal 1 — OpenOCD
```bash
openocd -f /home/jjsotoch/pulp/pulpissimo/target/fpga/pulpissimo-nexys/openocd-ft232h.cfg
```

### Terminal 2 — GDB
```bash
cd /home/jjsotoch/pulp/tfg-power/firmware/dominated_loops
gdb-multiarch float.elf
```

### Dentro de GDB
```gdb
target remote :3333
monitor reset halt
load
continue
```

La prueba termina sola en `ebreak`.

## Leer los CSR manualmente
Con la configuración actual de OpenOCD, los CSR custom se exponen como registros `csr3008` a `csr3019`.

```gdb
p/x $csr3008
p/x $csr3009
p/x $csr3010
p/x $csr3011
p/x $csr3012
p/x $csr3013
p/x $csr3014
p/x $csr3015
p/x $csr3016
p/x $csr3017
p/x $csr3018
p/x $csr3019
```

Si quieres todos en una sola línea:
```gdb
info registers csr3008 csr3009 csr3010 csr3011 csr3012 csr3013 csr3014 csr3015 csr3016 csr3017 csr3018 csr3019
```

Valor de 64 bits:
```gdb
p/u (unsigned long long)$csr3018 + ((unsigned long long)$csr3019 << 32)
```

## Mapeo de CSR
| CSR | Nombre |
|-----|--------|
| `0xBC0` | `ARITH_LO` |
| `0xBC1` | `ARITH_HI` |
| `0xBC2` | `LOGIC_LO` |
| `0xBC3` | `LOGIC_HI` |
| `0xBC4` | `MEMORY_LO` |
| `0xBC5` | `MEMORY_HI` |
| `0xBC6` | `BRANCH_LO` |
| `0xBC7` | `BRANCH_HI` |
| `0xBC8` | `JUMP_LO` |
| `0xBC9` | `JUMP_HI` |
| `0xBCA` | `FLOAT_LO` |
| `0xBCB` | `FLOAT_HI` |

## Ejemplo de compilación
### Test mínimo CSR
```bash
cd /home/jjsotoch/pulp/tfg-power/csr_test
/home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18/bin/riscv32-unknown-elf-gcc \
  -nostdlib -march=rv32imc -mabi=ilp32 -T csr_test.ld csr_test.S -o csr_test.elf
```

### Pruebas de bucles dominados
```bash
cd /home/jjsotoch/pulp/tfg-power/firmware/dominated_loops
make -B float.elf
make -B arith.elf
make -B logic.elf
make -B memory.elf
make -B branch.elf
make -B jump.elf
```

## Síntesis FPGA
```bash
cd /home/jjsotoch/pulp/pulpissimo/target/fpga/pulpissimo-nexys
source /home/jjsotoch/Documents/viv/Vivado/2022.1/settings64.sh
vsynth
```

`vsynth` usa `run_batch.tcl`, que debe existir en esa carpeta.
