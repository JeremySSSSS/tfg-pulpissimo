# Metodo 1 (bucles dominados) — un .elf por categoria, cada prueba ~32 s a 10 MHz.
# Cada <cat>.S es un programa autocontenido (solo incluye platform.inc).
RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-

CC      := $(CROSS)gcc
OBJDUMP := $(CROSS)objdump
SIZE    := $(CROSS)size

CATS := alu mul mulh div mem ctrl float idle
# Programas de validacion sinteticos: mezclan las 7 categorias (usan float).
MIXES := mix1 mix2 mix3
# Programas REALES (benchmarks): kernel C + harness.S. aes=crypto, dijkstra=grafos.
# Mezcla natural de instrucciones que decide el compilador. (nbody descartado:
# este bitstream se traba con cadenas seriales de dependencia FP, ver fir/dotprod.)
REAL := aes dijkstra sha256 primes mandel conv
ELFS  := $(addsuffix .elf,$(CATS)) $(addsuffix .elf,$(MIXES)) $(addsuffix .elf,$(REAL))

FLAGS := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.

# Para kernels C: evita que el compilador invente memcpy/memset o builtins.
KFLAGS := $(FLAGS) -fno-builtin -fno-tree-loop-distribute-patterns

# Enteras en rv32imc; float y los mix necesitan la extension F.
ARCH       := rv32imc
float.elf: ARCH := rv32imfc
mix1.elf:  ARCH := rv32imfc
mix2.elf:  ARCH := rv32imfc
mix3.elf:  ARCH := rv32imfc

.PHONY: all clean disassemble sizes
all: $(ELFS)

# Cada .elf de categoria/mix se compila de su unico .S (+ includes de plataforma).
%.elf: %.S platform.inc link.ld
	$(CC) $(FLAGS) -march=$(ARCH) -o $@ $<

# Programas reales: harness.S (ventana GPIO + dump) + un kernel C con run_workload().
# REPS ajustable para la duracion (la T real la mide mcycle; ~15-30 s a 10 MHz).
aes.elf:      harness.S wl_aes.c      platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=150000 -o $@ harness.S wl_aes.c
dijkstra.elf: harness.S wl_dijkstra.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=4000 -o $@ harness.S wl_dijkstra.c
sha256.elf:   harness.S wl_sha256.c   platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=70000 -o $@ harness.S wl_sha256.c
primes.elf:   harness.S wl_primes.c   platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=60 -o $@ harness.S wl_primes.c
mandel.elf:   harness.S wl_mandel.c   platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -DREPS=35 -o $@ harness.S wl_mandel.c
conv.elf:     harness.S wl_conv.c     platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=22000 -o $@ harness.S wl_conv.c

disassemble: all
	@for elf in $(ELFS); do \
		$(OBJDUMP) -d -M no-aliases $$elf > $${elf%.elf}.dis; \
	done

sizes: all
	$(SIZE) $(ELFS)

clean:
	rm -f *.elf *.dis
