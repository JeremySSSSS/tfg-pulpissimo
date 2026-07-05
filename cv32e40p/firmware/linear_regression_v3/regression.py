#!/usr/bin/env python3
"""Regresion lineal de potencia con intercepto para el clasificador v2.

Modelo:
  P = P0 + e_alu*r_alu + e_mul*r_mul + e_mulh*r_mulh
         + p_div*r_divcyc + e_mem*r_mem + e_ctrl*r_ctrl
         + e_float*r_float

donde r_i = contador_i / T. DIV usa DIVCYC, no n_div.
"""
import csv
import os
import sys

try:
    import numpy as np
except ImportError:
    sys.exit("Falta numpy: pip install numpy")

F_CLK = 10e6
MASK32 = 0xFFFFFFFF
FEATURES = [
    ("e_alu", 0, "nJ/instr"),
    ("e_mul", 2, "nJ/instr"),
    ("e_mulh", 4, "nJ/instr"),
    ("p_div", 14, "nJ/ciclo"),
    ("e_mem", 8, "nJ/instr"),
    ("e_ctrl", 10, "nJ/instr"),
    ("e_float", 12, "nJ/instr"),
]


def parse_int(value):
    return int(value.strip(), 0)


def load_runs(path):
    with open(path, encoding="ascii") as source:
        lines = [line for line in source if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        return []

    runs = []
    for row in csv.DictReader(lines):
        words = [parse_int(row[f"w{i}"]) for i in range(18)]
        cycles = (words[17] - words[16]) & MASK32
        if cycles == 0:
            raise ValueError(f"{row['profile']}: intervalo de cero ciclos")
        seconds = cycles / F_CLK
        counts = np.array(
            [words[lo] + (words[lo + 1] << 32) for _, lo, _ in FEATURES],
            dtype=float,
        )
        rates_million = counts / seconds / 1e6
        runs.append({
            "profile": row["profile"].strip(),
            "repeat": row["repeat"].strip(),
            "role": row.get("role", "train").strip().lower() or "train",
            "power": float(row["p_avg_w"]),
            "cycles": cycles,
            "seconds": seconds,
            "counts": counts,
            "rates": rates_million,
        })
    return runs


def design(rows):
    rates = np.vstack([row["rates"] for row in rows])
    return np.column_stack([np.ones(len(rows)), rates])


def fit(rows):
    x = design(rows)
    y = np.array([row["power"] for row in rows])
    beta, _, rank, singular = np.linalg.lstsq(x, y, rcond=None)
    pred = x @ beta
    residual = y - pred

    dof = len(y) - x.shape[1]
    if dof > 0 and rank == x.shape[1]:
        sigma2 = float(residual @ residual / dof)
        covariance = sigma2 * np.linalg.pinv(x.T @ x)
        stderr = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    else:
        stderr = np.full(x.shape[1], np.nan)

    # Diagnostico de condicion sin depender de las unidades de cada columna.
    features = x[:, 1:]
    scale = features.std(axis=0)
    if np.any(scale == 0):
        condition = float("inf")
    else:
        z = (features - features.mean(axis=0)) / scale
        condition = float(np.linalg.cond(np.column_stack([np.ones(len(z)), z])))

    return beta, stderr, pred, residual, rank, condition


def grouped_cv(rows):
    profiles = sorted({row["profile"] for row in rows})
    errors = []
    for profile in profiles:
        train = [row for row in rows if row["profile"] != profile]
        test = [row for row in rows if row["profile"] == profile]
        x = design(train)
        if len(train) < x.shape[1] or np.linalg.matrix_rank(x) < x.shape[1]:
            continue
        beta = np.linalg.lstsq(x, np.array([row["power"] for row in train]), rcond=None)[0]
        for row, predicted in zip(test, design(test) @ beta):
            errors.append((profile, row["power"], float(predicted)))
    return errors


def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs.csv")
    runs = load_runs(path)
    if not runs:
        sys.exit("runs.csv no contiene mediciones. Siga README.md y agregue las filas.")

    train = [row for row in runs if row["role"] == "train"]
    test = [row for row in runs if row["role"] == "test"]
    required = len(FEATURES) + 1
    if len(train) < required:
        sys.exit(f"Se requieren al menos {required} mediciones de entrenamiento; hay {len(train)}")
    if len(train) == required:
        print("Aviso: sistema justo-determinado; no habra grados de libertad para stderr.")

    beta, stderr, pred, residual, rank, condition = fit(train)
    y = np.array([row["power"] for row in train])
    ss_res = float(residual @ residual)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot else float("nan")
    rmse_mw = 1000.0 * float(np.sqrt(np.mean(residual ** 2)))

    print("=" * 72)
    print(f"Regresion lineal con intercepto: {len(train)} train, {len(test)} test")
    print("Modelo ajustado sobre potencia y tasas de eventos; f_clk=10 MHz")
    print("=" * 72)
    print(f"P0       = {beta[0]:.6f} +/- {stderr[0]:.6f} W")
    for index, (name, _, unit) in enumerate(FEATURES, start=1):
        # beta: W por (millones de eventos/s) = 1000 nJ/evento.
        value_nj = beta[index] * 1000.0
        error_nj = stderr[index] * 1000.0
        print(f"{name:8s} = {value_nj:11.3f} +/- {error_nj:9.3f} {unit}")

    print(f"\nR2 potencia train       = {r2:.6f}")
    print(f"RMSE potencia train     = {rmse_mw:.3f} mW")
    print(f"Rango potencia train    = {(y.max()-y.min())*1000:.3f} mW")
    print(f"Rango matriz            = {rank}/{required}")
    print(f"Condicion estandarizada = {condition:.2f}")

    print("\nAjuste por medicion:")
    print(f"{'perfil':24s} {'rep':>4s} {'T[s]':>8s} {'Pmed':>9s} {'Pest':>9s} {'err[mW]':>9s}")
    for row, estimated in zip(train, pred):
        print(f"{row['profile']:24s} {row['repeat']:>4s} {row['seconds']:8.3f} "
              f"{row['power']:9.5f} {estimated:9.5f} {(estimated-row['power'])*1000:9.3f}")

    if test:
        print("\nValidacion reservada:")
        x_test = design(test)
        pred_test = x_test @ beta
        for row, estimated in zip(test, pred_test):
            error_pct = 100.0 * (estimated - row["power"]) / row["power"]
            print(f"{row['profile']:24s} Pmed={row['power']:.5f} W "
                  f"Pest={estimated:.5f} W err={error_pct:+.3f}%")

    cv = grouped_cv(train)
    if cv:
        cv_error = np.array([estimated - measured for _, measured, estimated in cv])
        print(f"\nCV dejando un perfil fuera: RMSE={np.sqrt(np.mean(cv_error**2))*1000:.3f} mW, "
              f"MAE={np.mean(np.abs(cv_error))*1000:.3f} mW")
    else:
        print("\nCV por perfil no disponible: algun pliegue pierde rango completo.")

    negative = [FEATURES[i-1][0] for i in range(1, len(beta)) if beta[i] < 0]
    if negative:
        print("\nADVERTENCIA: coeficientes negativos: " + ", ".join(negative))
        print("La variacion medida no separa esas categorias del ruido/colinealidad.")
    if condition > 100:
        print("ADVERTENCIA: matriz mal condicionada; agregue perfiles o repeticiones.")
    if (y.max() - y.min()) * 1000 < 5 * rmse_mw:
        print("ADVERTENCIA: el rango de potencia es pequeno frente al error residual.")

    output = os.path.join(os.path.dirname(path), "coefficients.csv")
    with open(output, "w", newline="", encoding="ascii") as target:
        writer = csv.writer(target)
        writer.writerow(["coefficient", "value", "stderr", "unit"])
        writer.writerow(["P0", beta[0], stderr[0], "W"])
        for index, (name, _, unit) in enumerate(FEATURES, start=1):
            writer.writerow([name, beta[index] * 1000.0, stderr[index] * 1000.0, unit])
    print(f"\nCoeficientes guardados en {output}")


if __name__ == "__main__":
    main()
