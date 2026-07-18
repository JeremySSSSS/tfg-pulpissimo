# Benchmarks de validacion del modelo (held-out, NUNCA usados en calibracion).
# Todos en assembly (.S): cada ELF = harness.S + wl_<nombre>.S.
# Los float usan SOLO el set FP probado en HW (fadd/fmul/fsub/fmax
# independientes, sin fmadd/cadenas seriales); ver comentario de cada wl_*.S.
RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-
CC    := $(CROSS)gcc

BENCH_INT := sha256 primes conv floyd bitcount fixmul bsearch wmul divsum mixed
BENCH_FP  := fpgain fpalu fpmem ycbcr
# Cargas REALES: kernels de BEEBS (Pallister et al. 2013) sin modificar, en
# beebs/<nombre>.c, adaptados por beebs_wrap.c (interfaz initialise/benchmark/
# verify -> run_workload). REPS apunta a ventanas de ~15-35 s a 10 MHz;
# ajustar tras la primera corrida si la ventana queda corta o larga.
BENCH_BEEBS := mont64 ud jfdctint nettleaes dijkstra huffbench levenshtein ns aqsort
# gray: la unica propia (float); los kernels float de BEEBS usan double o
# acumulaciones dependientes que la FPU de este bitstream no ejecuta estable
BENCH_C_FP := gray
ELFS := $(addsuffix .elf,$(BENCH_INT) $(BENCH_FP) $(BENCH_BEEBS) $(BENCH_C_FP))

mont64.elf:      REPS := 20000
ud.elf:          REPS := 30000
jfdctint.elf:    REPS := 30000
nettleaes.elf:   REPS := 3000
dijkstra.elf:    REPS := 500
huffbench.elf:   REPS := 300
levenshtein.elf: REPS := 2000
ns.elf:          REPS := 10000
aqsort.elf:      REPS := 3000
aqsort.elf:      KFLAGS += -DQUICK_SORT
# fqsort (qsort de BEEBS sobre floats): RETIRADO. Solo usa flw/fsw y
# comparaciones fle.s/flt.s, pero su lazo interno (load->flt.s->branch
# pegados) COLGO en hardware: tercera evidencia de la restriccion de la
# FPU del bitstream (cadenas dependientes, rafagas densas y ahora
# comparaciones densas). La carga float real queda en gray (aritmetica
# espaciada con memoria, el patron probado).
# fqsort.elf:      REPS := 4000
# fqsort.elf:      ARCH := rv32imfc
# fqsort.elf:      KFLAGS += -ffp-contract=off

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

# -lgcc: algun kernel (ud) usa double en su verify_benchmark (fuera de la
# ventana de medicion); el soft-float lo aporta libgcc
%.elf: beebs/%.c beebs_wrap.c beebs/support.h harness.S platform.inc link.ld
	$(CC) $(KFLAGS) -march=$(ARCH) -Ibeebs -DNDEBUG -DREPS=$(REPS) -o $@ harness.S beebs_wrap.c $< -lgcc

clean:
	rm -f $(ELFS)
