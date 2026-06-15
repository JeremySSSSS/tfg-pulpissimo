# Metodo 1 (bucles dominados) — un .elf por categoria, cada prueba ~32 s a 10 MHz.
# Cada <cat>.S es un programa autocontenido (solo incluye platform.inc).
RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-

CC      := $(CROSS)gcc
OBJDUMP := $(CROSS)objdump
SIZE    := $(CROSS)size

CATS := alu mul mulh div mem ctrl float idle
# Programas de validacion: mezclan las 7 categorias (todos usan float -> rv32imfc).
MIXES := mix1 mix2 mix3
ELFS  := $(addsuffix .elf,$(CATS)) $(addsuffix .elf,$(MIXES))

FLAGS := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.

# Enteras en rv32imc; float y los mix necesitan la extension F.
ARCH       := rv32imc
float.elf: ARCH := rv32imfc
mix1.elf:  ARCH := rv32imfc
mix2.elf:  ARCH := rv32imfc
mix3.elf:  ARCH := rv32imfc

.PHONY: all clean disassemble sizes
all: $(ELFS)

# Cada .elf se compila de su unico .S (+ includes de plataforma).
%.elf: %.S platform.inc link.ld
	$(CC) $(FLAGS) -march=$(ARCH) -o $@ $<

disassemble: all
	@for elf in $(ELFS); do \
		$(OBJDUMP) -d -M no-aliases $$elf > $${elf%.elf}.dis; \
	done

sizes: all
	$(SIZE) $(ELFS)

clean:
	rm -f *.elf *.dis
