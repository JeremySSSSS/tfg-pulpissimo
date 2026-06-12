RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-

CC      := $(CROSS)gcc
OBJDUMP := $(CROSS)objdump
SIZE    := $(CROSS)size

LOOP_COUNT ?= 2000000
HALF_PERIOD_CYCLES ?= 5000000

COMMON_FLAGS := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I.

INTEGER_CATEGORIES := arith logic memory branch jump
INTEGER_ELFS := $(addsuffix .elf,$(INTEGER_CATEGORIES))
ALL_ELFS := $(INTEGER_ELFS) float.elf frequency_probe.elf

.PHONY: all clean disassemble sizes

all: $(ALL_ELFS)

$(INTEGER_ELFS): %.elf: %.S platform.inc link.ld
	$(CC) $(COMMON_FLAGS) -march=rv32imc \
		-DLOOP_COUNT=$(LOOP_COUNT) \
		-o $@ $<

float.elf: float.S platform.inc link.ld
	$(CC) $(COMMON_FLAGS) -march=rv32imfc \
		-DLOOP_COUNT=$(LOOP_COUNT) \
		-o $@ $<

frequency_probe.elf: frequency_probe.S platform.inc link.ld
	$(CC) $(COMMON_FLAGS) -march=rv32imc \
		-DHALF_PERIOD_CYCLES=$(HALF_PERIOD_CYCLES) \
		-o $@ frequency_probe.S

disassemble: all
	@for elf in $(ALL_ELFS); do \
		$(OBJDUMP) -d -M no-aliases $$elf > $${elf%.elf}.dis; \
	done

sizes: all
	$(SIZE) $(ALL_ELFS)

clean:
	rm -f *.elf *.dis

float_current.elf: float_current.S platform.inc link.ld
	$(CC) $(COMMON_FLAGS) -march=rv32imfc \
		-DLOOP_COUNT=100000 \
		-o $@ $<
