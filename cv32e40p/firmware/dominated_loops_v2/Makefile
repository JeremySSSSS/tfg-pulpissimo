RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-

CC      := $(CROSS)gcc
OBJDUMP := $(CROSS)objdump
SIZE    := $(CROSS)size

LOOP_COUNT ?= 2000000
# idle hace ~4 ciclos/iter (vs ~68 de los loops): ~17x mas iteraciones para
# durar lo mismo (~13 s) y dar un P_base estable en equilibrio termico.
IDLE_LOOP_COUNT ?= 34000000
# Categorias multiciclo: menos iteraciones para durar ~13 s (no 5 min).
# div ~25-32 cic/op, mulh ~4, ctrl(j) ~3, float ~2-3.
DIV_LOOP_COUNT   ?= 90000
MULH_LOOP_COUNT  ?= 500000
CTRL_LOOP_COUNT  ?= 700000
FLOAT_LOOP_COUNT ?= 1500000
VALID_LOOP_COUNT ?= 1500000

COMMON_FLAGS := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.

# Categorias enteras (rv32imc) + float (rv32imfc).
INT_CATS := alu mul mulh div mem ctrl idle
INT_ELFS := $(addsuffix .elf,$(INT_CATS))
# Cargas REALES (Metodo 2): programas con mezcla natural de instrucciones.
WL_ELFS  := sort.elf matmul.elf crc.elf strings.elf gcd.elf fir.elf bsearch.elf dotprod.elf
ALL_ELFS := $(INT_ELFS) float.elf $(WL_ELFS)

# Macro -DCATEGORY_<X> por target.
alu.elf:  CATDEF := -DCATEGORY_ALU
mul.elf:  CATDEF := -DCATEGORY_MUL
mulh.elf: CATDEF := -DCATEGORY_MULH
div.elf:  CATDEF := -DCATEGORY_DIV
mem.elf:  CATDEF := -DCATEGORY_MEM
ctrl.elf: CATDEF := -DCATEGORY_CTRL
idle.elf: CATDEF := -DCATEGORY_IDLE

# Conteo de iteraciones por target: idle dura mas para igualar el tiempo.
$(INT_ELFS): LC := $(LOOP_COUNT)
idle.elf:    LC := $(IDLE_LOOP_COUNT)
div.elf:     LC := $(DIV_LOOP_COUNT)
mulh.elf:    LC := $(MULH_LOOP_COUNT)
ctrl.elf:    LC := $(CTRL_LOOP_COUNT)

.PHONY: all clean disassemble sizes
all: $(ALL_ELFS)

$(INT_ELFS): %.elf: dominated_loop_v2.S platform.inc link.ld
	$(CC) $(COMMON_FLAGS) -march=rv32imc \
		-DLOOP_COUNT=$(LC) $(CATDEF) \
		-o $@ dominated_loop_v2.S

float.elf: dominated_loop_v2.S platform.inc link.ld
	$(CC) $(COMMON_FLAGS) -march=rv32imfc \
		-DLOOP_COUNT=$(FLOAT_LOOP_COUNT) -DCATEGORY_FLOAT \
		-o $@ dominated_loop_v2.S

# Cargas reales: harness.S (envoltura GPIO/CSR) + un kernel .c. REPS tuneable.
KFLAGS = -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I. \
	-fno-builtin -fno-tree-loop-distribute-patterns
sort.elf:    harness.S wl_sort.c    platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=20000  -o $@ harness.S wl_sort.c
matmul.elf:  harness.S wl_matmul.c  platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=6000   -o $@ harness.S wl_matmul.c
crc.elf:     harness.S wl_crc.c     platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=40000  -o $@ harness.S wl_crc.c
strings.elf: harness.S wl_strings.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=200000 -o $@ harness.S wl_strings.c
gcd.elf:     harness.S wl_gcd.c     platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=30000  -o $@ harness.S wl_gcd.c
valid.elf: mixed_validation.S platform.inc link.ld
	$(CC) $(COMMON_FLAGS) -march=rv32imfc \
		-DLOOP_COUNT=$(VALID_LOOP_COUNT) -o $@ mixed_validation.S
fir.elf:     harness.S wl_fir.c     platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -ffp-contract=off -DREPS=2000 -o $@ harness.S wl_fir.c
bsearch.elf: harness.S wl_bsearch.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc  -DREPS=2000000 -o $@ harness.S wl_bsearch.c
dotprod.elf: harness.S wl_dotprod.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -ffp-contract=off -DREPS=120000 -o $@ harness.S wl_dotprod.c

disassemble: all
	@for elf in $(ALL_ELFS); do \
		$(OBJDUMP) -d -M no-aliases $$elf > $${elf%.elf}.dis; \
	done

sizes: all
	$(SIZE) $(ALL_ELFS)

clean:
	rm -f *.elf *.dis
