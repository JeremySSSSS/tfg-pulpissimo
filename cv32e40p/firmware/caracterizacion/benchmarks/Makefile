# Benchmarks de validacion del modelo. Version assembly-only: cada ELF se
# construye a partir de un .S + harness.S + platform.inc.
RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-
CC    := $(CROSS)gcc

BENCH := sha256 primes conv md5 floyd bitcount ycbcr fpgain whetstone linpack livermore float_dominated_loops logistic
ELFS  := $(addsuffix .elf,$(BENCH))

FLAGS  := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.
KFLAGS := $(FLAGS) -fno-builtin -fno-tree-loop-distribute-patterns

.PHONY: all clean
all: $(ELFS)

sha256.elf: harness.S wl_sha256.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -o $@ harness.S wl_sha256.S
primes.elf: harness.S wl_primes.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -o $@ harness.S wl_primes.S
conv.elf:   harness.S wl_conv.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -o $@ harness.S wl_conv.S
md5.elf:    harness.S wl_md5.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -o $@ harness.S wl_md5.S
floyd.elf:  harness.S wl_floyd.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -o $@ harness.S wl_floyd.S
bitcount.elf: harness.S wl_bitcount.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -o $@ harness.S wl_bitcount.S
ycbcr.elf:  harness.S wl_ycbcr.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -o $@ harness.S wl_ycbcr.S
fpgain.elf:  harness.S wl_fpgain.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -o $@ harness.S wl_fpgain.S

whetstone.elf: harness.S wl_whetstone.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -o $@ harness.S wl_whetstone.S
linpack.elf:   harness.S wl_linpack.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -o $@ harness.S wl_linpack.S
livermore.elf: harness.S wl_livermore.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -o $@ harness.S wl_livermore.S
float_dominated_loops.elf: harness.S wl_float_dominated_loops.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -o $@ harness.S wl_float_dominated_loops.S
# logistico: float REGISTER-ONLY (sin flw/FMA/fcvt en el lazo) -> el unico float que la FPU banca
logistic.elf: harness.S wl_logistic.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -mabi=ilp32 -o $@ harness.S wl_logistic.S

clean:
	rm -f $(ELFS)
