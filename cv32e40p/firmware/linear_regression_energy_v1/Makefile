RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-

CC      := $(CROSS)gcc
OBJDUMP := $(CROSS)objdump
SIZE    := $(CROSS)size

COMMON_FLAGS := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.

ELFS := m00_mix.elf m01_mix.elf m02_mix.elf m03_mix.elf \
	m04_mix.elf m05_mix.elf m06_mix.elf m07_mix.elf \
	m08_mix.elf m09_mix.elf m10_mix.elf m11_mix.elf

m00_mix.elf: PROFILE := 0
m01_mix.elf: PROFILE := 1
m02_mix.elf: PROFILE := 2
m03_mix.elf: PROFILE := 3
m04_mix.elf: PROFILE := 4
m05_mix.elf: PROFILE := 5
m06_mix.elf: PROFILE := 6
m07_mix.elf: PROFILE := 7
m08_mix.elf: PROFILE := 8
m09_mix.elf: PROFILE := 9
m10_mix.elf: PROFILE := 10
m11_mix.elf: PROFILE := 11

LOOP_COUNT ?= 300000

.PHONY: all clean disassemble sizes
all: $(ELFS)

$(ELFS): %.elf: energy_mix.S platform.inc link.ld
	$(CC) $(COMMON_FLAGS) -march=rv32imfc -DPROFILE=$(PROFILE) -DLOOP_COUNT=$(LOOP_COUNT) -o $@ energy_mix.S

disassemble: $(ELFS)
	@for elf in $(ELFS); do \
		$(OBJDUMP) -d -M no-aliases $$elf > $${elf%.elf}.dis; \
	done

sizes: $(ELFS)
	$(SIZE) $(ELFS)

clean:
	rm -f $(ELFS) $(ELFS:.elf=.dis) coefficients.csv
