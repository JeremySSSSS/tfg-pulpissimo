target remote :3333
monitor reset halt
load
continue
printf "\n==== TEMPERATURA DEL DIE (XADC) ====\n"
printf "lecturas    : %d\n", g_count
printf "codigo crudo: %d  (0x%03x)\n", g_temp_code, g_temp_code
printf "temperatura : %d.%02d C\n", g_temp_cC/100, (g_temp_cC<0?-g_temp_cC:g_temp_cC)%100
printf "====================================\n"
