# Benchmarks de validacion del modelo (chopper). Cada uno = harness.S (ventana
# GPIO + dump de contadores) + un kernel C real con run_workload(). Sin FP en
# cadena serial (este bitstream cuelga la FPU con cadenas FP dependientes).
RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-
CC    := $(CROSS)gcc

BENCH := sha256 primes conv md5 floyd bitcount ycbcr
ELFS  := $(addsuffix .elf,$(BENCH))

FLAGS  := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.
KFLAGS := $(FLAGS) -fno-builtin -fno-tree-loop-distribute-patterns

.PHONY: all clean
all: $(ELFS)

# REPS ajusta la duracion (la T real la mide mcycle).
sha256.elf: harness.S wl_sha256.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=70000 -o $@ harness.S wl_sha256.c
primes.elf: harness.S wl_primes.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=60    -o $@ harness.S wl_primes.c
conv.elf:   harness.S wl_conv.c   platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=22000 -o $@ harness.S wl_conv.c
md5.elf:      harness.S wl_md5.c      platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=120000 -o $@ harness.S wl_md5.c
floyd.elf:    harness.S wl_floyd.c    platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=400    -o $@ harness.S wl_floyd.c
bitcount.elf: harness.S wl_bitcount.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=5000   -o $@ harness.S wl_bitcount.c
ycbcr.elf:    harness.S wl_ycbcr.c    platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -DREPS=1000 -o $@ harness.S wl_ycbcr.c
# DIAGNOSTICO float: sin FMA (-ffp-contract=off) y el .c no usa fcvt -> aisla el trigger del deadlock.
fpgain.elf:   harness.S wl_fpgain.c   platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -ffp-contract=off -DREPS=2000 -o $@ harness.S wl_fpgain.c

clean:
	rm -f $(ELFS)
