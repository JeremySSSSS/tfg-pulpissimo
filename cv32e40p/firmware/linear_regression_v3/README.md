# Caracterizacion por regresion lineal v3

Este experimento corrige el problema de repartir la potencia base entre todos
los coeficientes. Ajusta directamente:

```
P = P0 + e_alu*(n_alu/T) + e_mul*(n_mul/T) + e_mulh*(n_mulh/T)
       + p_div*(DIVCYC/T) + e_mem*(n_mem/T)
       + e_ctrl*(n_ctrl/T) + e_float*(n_float/T)
```

`P0` es la potencia base activa. Division usa `DIVCYC`; `n_div` se conserva
solo para comprobar la latencia media.

## 1. Compilar

```bash
cd /home/jjsotoch/pulp/tfg-pulpissimo/cv32e40p/firmware/linear_regression_v3
make all
```

Se generan 10 ELF mixtos. Cada uno mezcla varias categorias y apunta a
12-15 s a 10 MHz; el tiempo exacto se toma de `mcycle`, por lo que no es
necesario que duren exactamente igual.

Perfiles:

| ELF | Contenido principal |
|---|---|
| `p08_alu_mul` .. `p11_float_mem` | mezclas de dos categorias |
| `p12_balanced` | mezcla de todas las categorias |
| `p13_alu_ctrl_float` .. `p17_mem_mul` | mezclas adicionales para desacoplar columnas |

## 2. Medir

Para cada ELF:

1. Cargar el ELF y ejecutar desde `_start`.
2. Promediar potencia solo mientras GPIO8 esta alto.
3. Al caer GPIO8, leer:

```gdb
x/18xw &results
```

4. Agregar una fila a `runs.csv` con la potencia y los 18 words.
5. Repetir al menos tres veces.

Use `role=train` para las mezclas usadas en el ajuste. Marque
`p12_balanced` y `p13_alu_ctrl_float` como `role=test` si quiere reservarlas
como validacion. Los perfiles puros/legados deben marcarse como `role=skip`.

Recomendaciones experimentales:

- Mantener bitstream, tension, reloj y punto de medida sin cambios.
- Esperar temperatura estable antes de comenzar.
- Alternar o aleatorizar el orden de los perfiles para reducir deriva termica.
- Hacer tres vueltas completas en vez de medir tres veces seguidas cada ELF.
- Orden sugerido para la primera vuelta: p08, p09, p10, p11, p14, p15,
  p16, p17.
- Si quiere validacion separada, reserve p12 y p13.
- No promediar muestras anteriores al flanco de subida ni posteriores al de
  bajada de GPIO8.

## 3. Ajustar

```bash
python3 regression.py
```

El solver reporta `P0`, coeficientes en nJ, incertidumbre, rango, condicion,
RMSE, validacion reservada y validacion cruzada dejando un perfil fuera.
Tambien escribe `coefficients.csv`.

No acepte el resultado solo por un R2 alto. Los criterios minimos son:

- rango completo de la matriz (`8/8`),
- condicion estandarizada preferiblemente menor que 100,
- coeficientes no negativos dentro de la incertidumbre,
- RMSE claramente menor que el rango de potencia medido,
- error bajo en perfiles marcados como `test`.
