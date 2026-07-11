# Variantes de ciclo de trabajo (barrido de intensidad estilo EfiMon).
# GENERADO por el asistente: REPS escalado a ~12s (d60) / ~6s (d30) de
# tiempo activo en 10 tandas con wfi entre ellas -> ventana ~20 s.
DUTY_ELFS := $(OUT)/crc_d60.elf $(OUT)/crc_d30.elf $(OUT)/dotprod_d60.elf $(OUT)/dotprod_d30.elf $(OUT)/fpoly_d60.elf $(OUT)/fpoly_d30.elf $(OUT)/fsm_d60.elf $(OUT)/fsm_d30.elf $(OUT)/gcd_d60.elf $(OUT)/gcd_d30.elf $(OUT)/histogram_d60.elf $(OUT)/histogram_d30.elf $(OUT)/matmul_d60.elf $(OUT)/matmul_d30.elf $(OUT)/memcpy_d60.elf $(OUT)/memcpy_d30.elf $(OUT)/modpow_d60.elf $(OUT)/modpow_d30.elf $(OUT)/mulhash64_d60.elf $(OUT)/mulhash64_d30.elf $(OUT)/mulhscale_d60.elf $(OUT)/mulhscale_d30.elf $(OUT)/radix_d60.elf $(OUT)/radix_d30.elf $(OUT)/sort_d60.elf $(OUT)/sort_d30.elf $(OUT)/trialdiv_d60.elf $(OUT)/trialdiv_d30.elf $(OUT)/vecscale_d60.elf $(OUT)/vecscale_d30.elf


$(OUT)/crc_d60.elf: harness.S wl_crc.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=9760 -DCHUNKS=10 -DSLEEP_TICKS=8000597 -o $@ harness.S wl_crc.c

$(OUT)/crc_d30.elf: harness.S wl_crc.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=4880 -DCHUNKS=10 -DSLEEP_TICKS=14001046 -o $@ harness.S wl_crc.c

$(OUT)/dotprod_d60.elf: harness.S wl_dotprod.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -ffp-contract=off -DREPS=60150 -DCHUNKS=10 -DSLEEP_TICKS=7999952 -o $@ harness.S wl_dotprod.c

$(OUT)/dotprod_d30.elf: harness.S wl_dotprod.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -ffp-contract=off -DREPS=30080 -DCHUNKS=10 -DSLEEP_TICKS=14002244 -o $@ harness.S wl_dotprod.c

$(OUT)/fpoly_d60.elf: harness.S wl_fpoly.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -ffp-contract=off -DREPS=64380 -DCHUNKS=10 -DSLEEP_TICKS=8000288 -o $@ harness.S wl_fpoly.c

$(OUT)/fpoly_d30.elf: harness.S wl_fpoly.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -ffp-contract=off -DREPS=32190 -DCHUNKS=10 -DSLEEP_TICKS=14000505 -o $@ harness.S wl_fpoly.c

$(OUT)/fsm_d60.elf: harness.S wl_fsm.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=15090 -DCHUNKS=10 -DSLEEP_TICKS=8000756 -o $@ harness.S wl_fsm.c

$(OUT)/fsm_d30.elf: harness.S wl_fsm.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=7540 -DCHUNKS=10 -DSLEEP_TICKS=13992044 -o $@ harness.S wl_fsm.c

$(OUT)/gcd_d60.elf: harness.S wl_gcd.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=6960 -DCHUNKS=10 -DSLEEP_TICKS=8001531 -o $@ harness.S wl_gcd.c

$(OUT)/gcd_d30.elf: harness.S wl_gcd.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=3480 -DCHUNKS=10 -DSLEEP_TICKS=14002679 -o $@ harness.S wl_gcd.c

$(OUT)/histogram_d60.elf: harness.S wl_histogram.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=15480 -DCHUNKS=10 -DSLEEP_TICKS=7999032 -o $@ harness.S wl_histogram.c

$(OUT)/histogram_d30.elf: harness.S wl_histogram.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=7740 -DCHUNKS=10 -DSLEEP_TICKS=13998306 -o $@ harness.S wl_histogram.c

$(OUT)/matmul_d60.elf: harness.S wl_matmul.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=4040 -DCHUNKS=10 -DSLEEP_TICKS=8009166 -o $@ harness.S wl_matmul.c

$(OUT)/matmul_d30.elf: harness.S wl_matmul.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=2020 -DCHUNKS=10 -DSLEEP_TICKS=14016042 -o $@ harness.S wl_matmul.c

$(OUT)/memcpy_d60.elf: harness.S wl_memcpy.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=27950 -DCHUNKS=10 -DSLEEP_TICKS=8001153 -o $@ harness.S wl_memcpy.c

$(OUT)/memcpy_d30.elf: harness.S wl_memcpy.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=13970 -DCHUNKS=10 -DSLEEP_TICKS=13997009 -o $@ harness.S wl_memcpy.c

$(OUT)/modpow_d60.elf: harness.S wl_modpow.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=21950 -DCHUNKS=10 -DSLEEP_TICKS=8001019 -o $@ harness.S wl_modpow.c

$(OUT)/modpow_d30.elf: harness.S wl_modpow.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=10970 -DCHUNKS=10 -DSLEEP_TICKS=13995405 -o $@ harness.S wl_modpow.c

$(OUT)/mulhash64_d60.elf: harness.S wl_mulhash64.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=56390 -DCHUNKS=10 -DSLEEP_TICKS=7999863 -o $@ harness.S wl_mulhash64.c

$(OUT)/mulhash64_d30.elf: harness.S wl_mulhash64.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=28200 -DCHUNKS=10 -DSLEEP_TICKS=14002243 -o $@ harness.S wl_mulhash64.c

$(OUT)/mulhscale_d60.elf: harness.S wl_mulhscale.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=160860 -DCHUNKS=10 -DSLEEP_TICKS=8000106 -o $@ harness.S wl_mulhscale.c

$(OUT)/mulhscale_d30.elf: harness.S wl_mulhscale.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=80430 -DCHUNKS=10 -DSLEEP_TICKS=14000186 -o $@ harness.S wl_mulhscale.c

$(OUT)/radix_d60.elf: harness.S wl_radix.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=17120 -DCHUNKS=10 -DSLEEP_TICKS=8001888 -o $@ harness.S wl_radix.c

$(OUT)/radix_d30.elf: harness.S wl_radix.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=8560 -DCHUNKS=10 -DSLEEP_TICKS=14003305 -o $@ harness.S wl_radix.c

$(OUT)/sort_d60.elf: harness.S wl_sort.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=15690 -DCHUNKS=10 -DSLEEP_TICKS=7998601 -o $@ harness.S wl_sort.c

$(OUT)/sort_d30.elf: harness.S wl_sort.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=7850 -DCHUNKS=10 -DSLEEP_TICKS=14006473 -o $@ harness.S wl_sort.c

$(OUT)/trialdiv_d60.elf: harness.S wl_trialdiv.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=18200 -DCHUNKS=10 -DSLEEP_TICKS=7998223 -o $@ harness.S wl_trialdiv.c

$(OUT)/trialdiv_d30.elf: harness.S wl_trialdiv.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imc -DREPS=9100 -DCHUNKS=10 -DSLEEP_TICKS=13996890 -o $@ harness.S wl_trialdiv.c

$(OUT)/vecscale_d60.elf: harness.S wl_vecscale.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -ffp-contract=off -DREPS=77720 -DCHUNKS=10 -DSLEEP_TICKS=7999979 -o $@ harness.S wl_vecscale.c

$(OUT)/vecscale_d30.elf: harness.S wl_vecscale.c platform.inc link.ld
	$(CC) $(KFLAGS) -march=rv32imfc -ffp-contract=off -DREPS=38860 -DCHUNKS=10 -DSLEEP_TICKS=13999963 -o $@ harness.S wl_vecscale.c
