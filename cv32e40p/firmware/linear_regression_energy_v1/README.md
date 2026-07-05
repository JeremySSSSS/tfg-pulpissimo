# Regresion por energia con mezclas balanceadas

Este experimento sigue el metodo correcto para el TFG:

1. Ejecutar varios scripts mixtos.
2. Medir la potencia promedio `P_avg` durante la ventana GPIO8.
3. Leer `mcycle` y los 16 CSR del clasificador.
4. Formar la energia por corrida `E = P_avg * T`.
5. Resolver el sistema lineal:

```text
E_k = P0*T_k + e_alu*n_alu,k + e_mul*n_mul,k + e_mulh*n_mulh,k
    + p_div*c_div,k + e_mem*n_mem,k + e_ctrl*n_ctrl,k + e_float*n_float,k
```

`c_div` es `DIVCYC`. Las instrucciones de CSR usadas como overhead no se
cuentan, pero ayudan a romper la dependencia exacta entre `T` y los conteos.

## Compilar

```bash
cd /home/jjsotoch/pulp/tfg-pulpissimo/cv32e40p/firmware/linear_regression_energy_v1
make all
```

## Scripts

Hay 12 perfiles, todos con las 7 categorias activas:

| ELF | Uso |
|---|---|
| `m00_mix` .. `m09_mix` | entrenamiento |
| `m10_mix`, `m11_mix` | validacion reservada |

## Medicion

Para cada ELF:

1. Cargar el programa.
2. Medir `P_avg` solo mientras GPIO8 esta alto.
3. Leer:

```gdb
x/18xw &results
```

4. Guardar una fila en `runs.csv`.

El orden recomendado es alternar perfiles de distinta mezcla para reducir deriva
termica. No mezcles este conjunto con los perfiles legados de los otros
directorios.

## Ajuste

```bash
python3 regression.py
```

El solver reporta `P0`, los coeficientes `e_i` en nJ, `R2`, RMSE y
validacion reservada.
