# Benchmarks de validacion del modelo (held-out, NUNCA usados en calibracion).
# Todos en assembly (.S): cada ELF = harness.S + wl_<nombre>.S.
# Los float usan SOLO el set FP probado en HW (fadd/fmul/fsub/fmax
# independientes, sin fmadd/cadenas seriales); ver comentario de cada wl_*.S.
RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-
CC    := $(CROSS)gcc

BENCH_INT := sha256 primes conv floyd bitcount fixmul bsearch wmul divsum mixed
BENCH_FP  := fpgain fpalu fpmem ycbcr
# Cargas REALES en C (algoritmos completos compilados por GCC, sin ajustar la
# mezcla de instrucciones). REPS apunta a ventanas de ~15-35 s a 10 MHz;
# ajustar tras la primera corrida si la ventana queda corta o larga.
BENCH_C    := aes128 dijkstra dct8x8 rle sieve qsort pctstats reloj
BENCH_C_FP := gray
ELFS := $(addsuffix .elf,$(BENCH_INT) $(BENCH_FP) $(BENCH_C) $(BENCH_C_FP))

FLAGS  := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.
KFLAGS := $(FLAGS) -fno-builtin -fno-tree-loop-distribute-patterns

ARCH := rv32imc
$(addsuffix .elf,$(BENCH_FP)): ARCH := rv32imfc
# gray es float en C: rv32imfc y SIN contraccion a fmadd (fuera del conjunto
# probado de la FPU de este bitstream)
gray.elf: ARCH := rv32imfc
gray.elf: KFLAGS += -ffp-contract=off

.PHONY: all clean
all: $(ELFS)

%.elf: wl_%.S harness.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=$(ARCH) -o $@ harness.S $<

%.elf: wl_%.c harness.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=$(ARCH) -o $@ harness.S $<

clean:
	rm -f $(ELFS)
