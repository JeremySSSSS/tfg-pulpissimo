# Chopper: un .elf por categoria. Cada fase (categoria / idle) dura ~0.3 s;
# CHOP_PAIRS=500 -> ~5 min total. CAT_ITERS ajustado por cyc/iter de cada
# categoria (de la calibracion M1) para que la fase categoria dure ~0.3 s
# (~3M ciclos a 10 MHz). IDLE_ITERS comun (idle ~4 cyc/iter).
RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-
CC      := $(CROSS)gcc
OBJDUMP := $(CROSS)objdump
SIZE    := $(CROSS)size

CATS := alu mul mulh div mem ctrl float
ELFS := $(addsuffix .elf,$(CATS))

FLAGS := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.

CHOP_PAIRS ?= 500
IDLE_ITERS ?= 3000      # con IDLE_NOPS=1000 -> ~0.3 s de fase idle
IDLE_NOPS  ?= 1000      # NOPs por iteracion idle (referencia pasiva)

# CAT_ITERS por categoria (~0.3 s de fase categoria)
alu.elf:   CAT := 44000
mul.elf:   CAT := 44000
mulh.elf:  CAT := 9300
div.elf:   CAT := 2200
mem.elf:   CAT := 22900
ctrl.elf:  CAT := 22700
float.elf: CAT := 35700

# Arquitectura: float necesita F.
ARCH       := rv32imc
float.elf: ARCH := rv32imfc

# Macro CATEGORY_<X> por target.
alu.elf:   CATDEF := -DCATEGORY_ALU
mul.elf:   CATDEF := -DCATEGORY_MUL
mulh.elf:  CATDEF := -DCATEGORY_MULH
div.elf:   CATDEF := -DCATEGORY_DIV
mem.elf:   CATDEF := -DCATEGORY_MEM
ctrl.elf:  CATDEF := -DCATEGORY_CTRL
float.elf: CATDEF := -DCATEGORY_FLOAT

.PHONY: all clean
all: $(ELFS)

$(ELFS): %.elf: chopper.S platform.inc link.ld
	$(CC) $(FLAGS) -march=$(ARCH) $(CATDEF) \
		-DCHOP_PAIRS=$(CHOP_PAIRS) -DCAT_ITERS=$(CAT) \
		-DIDLE_ITERS=$(IDLE_ITERS) -DIDLE_NOPS=$(IDLE_NOPS) \
		-o $@ chopper.S

clean:
	rm -f *.elf *.dis
