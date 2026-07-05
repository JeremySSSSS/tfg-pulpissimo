RISCV ?= /home/jjsotoch/pulp/toolchain/v1.0.16-pulp-riscv-gcc-ubuntu-18
CROSS := $(RISCV)/bin/riscv32-unknown-elf-
CC := $(CROSS)gcc
OBJDUMP := $(CROSS)objdump
SIZE := $(CROSS)size

COMMON_FLAGS := -nostdlib -nostartfiles -static -Os -g -mabi=ilp32 \
	-Wl,-T,link.ld -Wl,--build-id=none -I. -march=rv32imfc

ELFS := p08_alu_mul.elf p09_mem_ctrl.elf p10_mulh_div.elf \
	p11_float_mem.elf p12_balanced.elf p13_alu_ctrl_float.elf \
	p14_mul_mem_div.elf p15_alu_div.elf p16_mulh_float.elf \
	p17_mem_mul.elf

p00_base.elf:            PROFILE := 0
p01_alu.elf:             PROFILE := 1
p02_mul.elf:             PROFILE := 2
p03_mulh.elf:            PROFILE := 3
p04_div.elf:             PROFILE := 4
p05_mem.elf:             PROFILE := 5
p06_ctrl.elf:            PROFILE := 6
p07_float.elf:           PROFILE := 7
p08_alu_mul.elf:         PROFILE := 8
p09_mem_ctrl.elf:        PROFILE := 9
p10_mulh_div.elf:        PROFILE := 10
p11_float_mem.elf:       PROFILE := 11
p12_balanced.elf:        PROFILE := 12
p13_alu_ctrl_float.elf:  PROFILE := 13
p14_mul_mem_div.elf:     PROFILE := 14
p15_alu_div.elf:         PROFILE := 15
p16_mulh_float.elf:      PROFILE := 16
p17_mem_mul.elf:         PROFILE := 17
p18_base64.elf:          PROFILE := 18
p19_base128.elf:         PROFILE := 19

# Ajustados para aproximadamente 12 segundos a 10 MHz.
p00_base.elf:            LC := 910000
p01_alu.elf:             LC := 3500000
p02_mul.elf:             LC := 3500000
p03_mulh.elf:            LC := 1450000
p04_div.elf:             LC := 1400000
p05_mem.elf:             LC := 2100000
p06_ctrl.elf:            LC := 1800000
p07_float.elf:           LC := 2700000
p08_alu_mul.elf:         LC := 3500000
p09_mem_ctrl.elf:        LC := 1300000
p10_mulh_div.elf:        LC := 950000
p11_float_mem.elf:       LC := 2400000
p12_balanced.elf:        LC := 800000
p13_alu_ctrl_float.elf:  LC := 2300000
p14_mul_mem_div.elf:     LC := 1100000
p15_alu_div.elf:         LC := 1180000
p16_mulh_float.elf:      LC := 1900000
p17_mem_mul.elf:         LC := 2650000
p18_base64.elf:          LC := 465000
p19_base128.elf:         LC := 234000

.PHONY: all clean disassemble sizes
all: $(ELFS)

$(ELFS): %.elf: regression_mix.S platform.inc link.ld
	$(CC) $(COMMON_FLAGS) -DPROFILE=$(PROFILE) -DLOOP_COUNT=$(LC) -o $@ regression_mix.S

disassemble: $(ELFS)
	@for elf in $(ELFS); do \
		$(OBJDUMP) -d -M no-aliases $$elf > $${elf%.elf}.dis; \
	done

sizes: $(ELFS)
	$(SIZE) $(ELFS)

clean:
	rm -f $(ELFS) $(ELFS:.elf=.dis)
