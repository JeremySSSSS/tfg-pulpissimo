#!/usr/bin/env python3
"""I/O con el Google Sheet a traves del Web App (Apps Script), enrutando por
NOMBRE de pestaña (parametro 'hoja') -> no hacen falta GIDs.

  subir(hoja, **campos)  -> agrega una fila a esa pestaña
  leer(hoja)             -> lista de dicts (una por fila, por encabezado)
  ultima(hoja)           -> la ultima fila (dict) o None

El ESP32 sigue subiendo a 'inbox' (default del Apps Script) sin cambios.
"""
import csv
import io
import time
import urllib.error
import urllib.parse
import urllib.request

# URL del Web App (/exec). Actualizar tras redeployar el Apps Script.
SCRIPT_URL = "https://script.google.com/macros/s/REDACTED/exec"

REINTENTOS = 4   # el Apps Script da 500 transitorios (cold start, crear pestaña)


def _get(params):
    """GET al Web App con reintentos. El Apps Script lanza 500 transitorios
    (arranque en frio, insertSheet la 1.ra vez) -> reintenta con backoff."""
    url = f"{SCRIPT_URL}?{urllib.parse.urlencode(params)}"
    for intento in range(1, REINTENTOS + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode("utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            if intento == REINTENTOS:
                raise
            print(f"    [sheet] {e} (intento {intento}/{REINTENTOS}); reintento...")
            time.sleep(2 * intento)


def subir(hoja, **campos):
    """Agrega una fila a la pestaña 'hoja' con los campos dados."""
    return _get(dict(hoja=hoja, **campos))


def leer(hoja):
    """Devuelve las filas de la pestaña como lista de dicts (por encabezado)."""
    text = _get(dict(hoja=hoja, accion="leer"))
    rows = [r for r in csv.reader(io.StringIO(text)) if r]
    if len(rows) < 2:
        return []
    hdr = rows[0]
    return [dict(zip(hdr, r)) for r in rows[1:]]


def ultima(hoja):
    filas = leer(hoja)
    return filas[-1] if filas else None


def n_filas(hoja):
    return len(leer(hoja))


def fnum(x):
    """Numero del Sheet (locale es-ES: decimales con coma)."""
    return float(str(x).replace(",", "."))


class Inbox:
    """Espera las filas que sube el ESP32 a 'inbox' (una por ventana medida).
    Detecta fila nueva por conteo; get_pavg() bloquea hasta que aparezca."""

    def __init__(self, hoja="inbox"):
        self.hoja = hoja
        self.seen = n_filas(hoja)

    def get_pavg(self, timeout=30):
        t0 = time.time()
        while time.time() - t0 < timeout:
            filas = leer(self.hoja)
            if len(filas) > self.seen:
                self.seen = len(filas)
                return fnum(filas[-1]["p_avg"])
            print(f"    esperando P_avg del ESP32... ({time.time()-t0:4.0f}s/{timeout}s)")
            time.sleep(3)
        raise TimeoutError(f"timeout esperando fila nueva en '{self.hoja}'")
