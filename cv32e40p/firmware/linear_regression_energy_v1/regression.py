#!/usr/bin/env python3
"""Regresion por energia para perfiles mixtos balanceados.

Modelo:
    E_k = P0 * T_k + e_alu * n_alu,k + e_mul * n_mul,k + e_mulh * n_mulh,k
         + p_div * c_div,k + e_mem * n_mem,k + e_ctrl * n_ctrl,k
         + e_float * n_float,k

E_k = P_avg,k * T_k. DIV usa DIVCYC como contador de ciclos.
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
    ("P0", "T", "W"),
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
    runs = []
    for row in csv.DictReader(lines):
        if row["role"].strip().lower() == "skip":
            continue
        words = [parse_int(row[f"w{i}"]) for i in range(18)]
        cycles = (words[17] - words[16]) & MASK32
        if cycles == 0:
            raise ValueError(f"{row['profile']}: intervalo de cero ciclos")
        seconds = cycles / F_CLK
        counts = np.array(
            [
                words[0] + (words[1] << 32),
                words[2] + (words[3] << 32),
                words[4] + (words[5] << 32),
                words[14] + (words[15] << 32),
                words[8] + (words[9] << 32),
                words[10] + (words[11] << 32),
                words[12] + (words[13] << 32),
            ],
            dtype=float,
        )
        runs.append({
            "profile": row["profile"].strip(),
            "repeat": row["repeat"].strip(),
            "role": row["role"].strip().lower(),
            "power": float(row["p_avg_w"]),
            "seconds": seconds,
            "energy": float(row["p_avg_w"]) * seconds,
            "counts": counts,
        })
    return runs


def design(rows):
    t = np.array([row["seconds"] for row in rows], dtype=float)
    counts = np.vstack([row["counts"] for row in rows])
    return np.column_stack([t, counts])


def fit(rows):
    x = design(rows)
    y = np.array([row["energy"] for row in rows], dtype=float)
    beta, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    pred = x @ beta
    residual = y - pred
    dof = len(y) - x.shape[1]
    if dof > 0 and rank == x.shape[1]:
        sigma2 = float(residual @ residual / dof)
        cov = sigma2 * np.linalg.pinv(x.T @ x)
        stderr = np.sqrt(np.maximum(np.diag(cov), 0.0))
    else:
        stderr = np.full(x.shape[1], np.nan)
    cond = float(np.linalg.cond((x - x.mean(axis=0)) / x.std(axis=0)))
    return beta, stderr, pred, residual, rank, cond


def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs.csv")
    runs = load_runs(path)
    train = [row for row in runs if row["role"] == "train"]
    test = [row for row in runs if row["role"] == "test"]
    if len(train) < len(FEATURES):
        sys.exit(f"Se requieren al menos {len(FEATURES)} mediciones de entrenamiento; hay {len(train)}")

    beta, stderr, pred, residual, rank, cond = fit(train)
    y = np.array([row["energy"] for row in train], dtype=float)
    ss_res = float(residual @ residual)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot else float("nan")
    rmse = float(np.sqrt(np.mean(residual ** 2)))

    print("=" * 72)
    print(f"Regresion por energia: {len(train)} train, {len(test)} test")
    print("Modelo: E = P0*T + sum(e_i*n_i) + p_div*c_div")
    print("=" * 72)
    for i, (name, _, unit) in enumerate(FEATURES):
        if i == 0:
            print(f"{name:8s} = {beta[i]:12.6f} +/- {stderr[i]:.6f} {unit}")
        else:
            print(f"{name:8s} = {beta[i] * 1e9:12.3f} +/- {stderr[i] * 1e9:.3f} {unit}")

    print(f"\nR2 energia train       = {r2:.6f}")
    print(f"RMSE energia train     = {rmse*1e3:.3f} mJ")
    print(f"Rango matriz           = {rank}/{x.shape[1] if 'x' in locals() else len(FEATURES)}")
    print(f"Condicion              = {cond:.2f}")

    print("\nAjuste por medicion:")
    print(f"{'perfil':24s} {'rep':>4s} {'T[s]':>8s} {'Pmed':>9s} {'Emed[J]':>10s} {'Eest[J]':>10s}")
    for row, est in zip(train, pred):
        print(f"{row['profile']:24s} {row['repeat']:>4s} {row['seconds']:8.3f} "
              f"{row['power']:9.5f} {row['energy']:10.6f} {est:10.6f}")

    if test:
        print("\nValidacion reservada:")
        x_test = design(test)
        pred_test = x_test @ beta
        for row, est in zip(test, pred_test):
            err_pct = 100.0 * (est - row["energy"]) / row["energy"]
            print(f"{row['profile']:24s} Emed={row['energy']:.6f} J "
                  f"Eest={est:.6f} J err={err_pct:+.3f}%")

    out = os.path.join(os.path.dirname(path), "coefficients.csv")
    with open(out, "w", newline="", encoding="ascii") as target:
        writer = csv.writer(target)
        writer.writerow(["coefficient", "value", "stderr", "unit"])
        writer.writerow(["P0", beta[0], stderr[0], "W"])
        for i, (name, _, unit) in enumerate(FEATURES[1:], start=1):
            writer.writerow([name, beta[i] * 1e9, stderr[i] * 1e9, unit])
    print(f"\nCoeficientes guardados en {out}")


if __name__ == "__main__":
    main()
