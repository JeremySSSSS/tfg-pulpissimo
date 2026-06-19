# Chopper (referencia wfi): un .elf por categoria, desde su .S auto-contenido.
# Salida -> ../elf/.  float requiere la extension F (rv32imfc).
RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-
CC    := $(CROSS)gcc

CATS := alu mul mulh div mem ctrl float
OUT  := ../elf
ELFS := $(addprefix $(OUT)/,$(addsuffix .elf,$(CATS)))

FLAGS := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.

ARCH        := rv32imc
$(OUT)/float.elf: ARCH := rv32imfc

.PHONY: all clean
all: $(ELFS)

$(OUT)/%.elf: %.S platform.inc link.ld | $(OUT)
	$(CC) $(FLAGS) -march=$(ARCH) -o $@ $<

$(OUT):
	mkdir -p $(OUT)

clean:
	rm -f $(ELFS)
