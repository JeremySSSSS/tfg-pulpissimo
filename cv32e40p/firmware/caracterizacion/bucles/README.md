# bucles — método M1 (bucles dominados)

Datos y programas del método M1: microbenchmarks en ensamblador donde una sola
categoría domina el retiro, de modo que el coeficiente energético de esa categoría
se despeja directamente de la potencia medida, sin regresión.

- `fuentes/` — un bucle dominado por categoría (`alu`, `mul`, `mulh`, `div`, `mem`,
  `ctrl`, `float`) con su Makefile.
- `elf/` — binarios compilados que carga el banco.
- `datos.csv` — mediciones crudas (conteos CSR, potencia, temperatura) por corrida;
  las campañas se separan por las filas de idle que abren cada una.
- `coeficientes.csv` — coeficientes oficiales del método (campaña seleccionada).
- `campanas/` — respaldo de los coeficientes de cada campaña individual
  (`coeficientes_<timestamp>.csv`), para el análisis de reproducibilidad.

Se corre con `python3 ../caracterizar.py --metodo bucles` o desde la GUI.
