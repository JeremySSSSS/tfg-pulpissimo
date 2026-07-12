#!/usr/bin/env python3
"""Interfaz grafica (web local) para caracterizacion y validacion.

Envuelve los scripts existentes (caracterizar.py, verificar.py, pares.py,
reproducibilidad.py) SIN duplicar logica: cada boton lanza el script como
subproceso y la consola muestra su salida en vivo. Un solo trabajo a la vez
(el banco es exclusivo). Solo escucha en localhost.

Uso:
    python3 gui.py            # abre http://localhost:8237 (solo esta PC)
    python3 gui.py --lan      # ademas accesible desde la red local (telefono):
                              # http://<IP-de-esta-PC>:8237. OJO: cualquiera en
                              # tu WiFi podria operar el banco mientras corre.
"""
import json
import os
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "comun"))
import modelo  # noqa: E402

PORT = 8237
CATS = ["alu", "mul", "mulh", "div", "mem", "ctrl", "float"]
PROGS_M2 = ["memcpy", "fsm", "crc", "matmul", "mulhash64", "mulhscale", "dotprod",
            "gcd", "modpow", "trialdiv", "radix", "fpoly", "vecscale", "histogram", "sort"]


def benchmarks():
    d = os.path.join(HERE, "benchmarks")
    return sorted(f[:-4] for f in os.listdir(d) if f.endswith(".elf")) \
        if os.path.isdir(d) else []


# ---------------- trabajo en curso (uno a la vez: el banco es exclusivo) ----
class Trabajo:
    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.cola = []         # comandos pendientes (tandas multiples)
        self.nombre = ""
        self.log = []          # lineas acumuladas de la corrida actual
        self.inicio = None

    def corriendo(self):
        return self.proc is not None and self.proc.poll() is None

    def corriendo_o_encolado(self):
        return self.corriendo() or self.cola

    def lanzar(self, nombre, cmds):
        """cmds: lista de argv a correr EN SECUENCIA (p.ej. N campanas).
        Se aborta la cola si un comando falla o si el usuario detiene."""
        with self.lock:
            if self.corriendo_o_encolado():
                return False, f"ya hay un trabajo corriendo: {self.nombre}"
            self.nombre, self.log, self.inicio = nombre, [], time.time()
            self.cola = list(cmds)
            threading.Thread(target=self._correr_cola, daemon=True).start()
            return True, "lanzado"

    def _correr_cola(self):
        total = len(self.cola)
        i = 0
        while self.cola:
            i += 1
            cmd = self.cola.pop(0)
            if total > 1:
                self.log.append(f"===== tanda {i}/{total} =====")
            self.log.append(f"$ {' '.join(cmd)}")
            self.proc = subprocess.Popen(
                cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, start_new_session=True)
            for linea in self.proc.stdout:
                self.log.append(linea.rstrip("\n"))
            rc = self.proc.wait()
            if rc != 0 and self.cola:
                self.log.append(f"[GUI] rc={rc}: cancelo las {len(self.cola)} tandas restantes")
                self.cola = []
        dur = time.time() - self.inicio
        self.log.append(f"--- fin (rc={rc}, {dur/60:.1f} min) ---")

    def detener(self):
        if self.cola:
            self.log.append(f"[GUI] cola de {len(self.cola)} tandas cancelada")
            self.cola = []
        if self.corriendo():
            os.killpg(os.getpgid(self.proc.pid), signal.SIGINT)
            self.log.append("[GUI] SIGINT enviado (corte limpio)...")
            return True
        return False


JOB = Trabajo()

# ---------------- construccion de comandos (todo whitelisteado) -------------
PY = [sys.executable, "-u"]


def cmd_de(req):
    """req (dict del cliente) -> (nombre, [argv, ...]) o lanza ValueError."""
    a = req.get("accion")
    if a == "m1":
        cats = [c for c in req.get("cats", []) if c in CATS] or CATS
        cmd = PY + ["caracterizar.py", "bucles"] + cats
        rep = int(req.get("repeats", 1))
        if rep > 1:
            cmd += ["--repeats", str(min(rep, 30))]
        if req.get("nobuild"):
            cmd.append("--no-build")
        return f"M1 bucles ({','.join(cats)})", [cmd]
    if a == "m2":
        modelo_ = req.get("modelo", "efimon")
        if modelo_ not in ("clasico", "diferencial", "efimon"):
            raise ValueError("modelo invalido")
        progs = [p for p in req.get("progs", []) if p in PROGS_M2] or PROGS_M2
        cmd = PY + ["caracterizar.py", "regresion", "--modelo", modelo_] + progs
        if req.get("refit"):
            cmd.append("--refit")
        if req.get("nobuild"):
            cmd.append("--no-build")
        if req.get("refit"):
            return "M2 refit (sin hardware)", [cmd]
        # N campanas EN SECUENCIA (reproducibilidad): la 1.a compila (salvo que
        # ya se pidiera no hacerlo); las demas con --no-build -> ELF identicos
        n = min(max(int(req.get("campanas", 1)), 1), 10)
        cmds = [cmd] + [cmd + ["--no-build"] if "--no-build" not in cmd else cmd
                        for _ in range(n - 1)]
        suf = f" x{n} campanas" if n > 1 else ""
        return f"M2 regresion [{modelo_}]{suf}", cmds
    if a == "verificar":
        met = req.get("metodo")
        if met not in ("bucles", "regresion"):
            raise ValueError("metodo invalido")
        pidle = req.get("pidle", "temp")
        if pidle not in ("temp", "medir", "archivo"):
            raise ValueError("pidle invalido")
        progs = [p for p in req.get("progs", []) if p in benchmarks()]
        if not progs:
            raise ValueError("elegi al menos un benchmark")
        return (f"Verificar {met} ({len(progs)} prog)",
                [PY + ["verificar.py", "--metodo", met, "--pidle", pidle] + progs])
    if a == "pares":
        return "Pares diferenciales", [PY + ["pares.py"]]
    if a == "repro":
        return "Reproducibilidad (analisis, sin hardware)", [PY + ["reproducibilidad.py"]]
    raise ValueError(f"accion desconocida: {a}")


# ---------------- estado (coeficientes + ultima validacion) -----------------
def estado():
    est = {"coef": {}, "valid": []}
    for met in ("bucles", "regresion"):
        p = os.path.join(HERE, met, "coeficientes.csv")
        if os.path.exists(p):
            try:
                P_idle, coef = modelo.cargar_coeficientes(p)
                est["coef"][met] = {
                    "P_idle_W": round(P_idle, 6),
                    "fecha": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p))),
                    **{k: round(v * 1e9, 3) for k, v in coef.items() if k in CATS}}
            except Exception as e:
                est["coef"][met] = {"error": str(e)}
    vcsv = os.path.join(HERE, "verificacion.csv")
    if os.path.exists(vcsv):
        with open(vcsv) as f:
            filas = f.read().splitlines()[1:]
        for linea in filas[-10:]:
            c = linea.split(",")
            if len(c) >= 7:
                est["valid"].append({"fecha": c[0][5:16], "metodo": c[1],
                                     "programa": c[2], "err_pct": c[6]})
    return est


# ---------------- pagina --------------------------------------------------
def pagina():
    bm = benchmarks()
    chk = lambda ns, grp: "".join(  # noqa: E731
        f'<label class="chip"><input type="checkbox" name="{grp}" value="{n}" checked>{n}</label>'
        for n in ns)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Banco TFG &mdash; caracterizacion CV32E40P</title>
<style>
 body{{font-family:system-ui,sans-serif;margin:0;background:#12151a;color:#dde3ea}}
 header{{padding:10px 18px;background:#1b2129;border-bottom:1px solid #2c3540;
        display:flex;align-items:center;gap:14px}}
 header h1{{font-size:16px;margin:0}} #dot{{width:10px;height:10px;border-radius:50%;
        background:#4a5561}} #dot.on{{background:#37c871;box-shadow:0 0 8px #37c871}}
 main{{display:grid;grid-template-columns:390px 1fr;gap:12px;padding:12px}}
 @media(max-width:900px){{main{{grid-template-columns:1fr}}}}
 .card{{background:#1b2129;border:1px solid #2c3540;border-radius:8px;padding:12px;margin-bottom:12px}}
 .card h2{{font-size:13px;margin:0 0 8px;color:#8fb4d8;text-transform:uppercase;letter-spacing:.5px}}
 .chip{{display:inline-flex;align-items:center;gap:3px;background:#242c36;border:1px solid #2c3540;
       border-radius:12px;padding:2px 8px;margin:2px;font-size:12px;cursor:pointer}}
 .fila{{margin:6px 0;font-size:13px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
 button{{background:#2d6cdf;color:#fff;border:0;border-radius:6px;padding:6px 14px;
        font-size:13px;cursor:pointer}} button:disabled{{background:#4a5561;cursor:not-allowed}}
 button.rojo{{background:#c0392b}} select,input[type=number]{{background:#242c36;color:#dde3ea;
        border:1px solid #2c3540;border-radius:4px;padding:3px 6px}}
 #log{{background:#0d1013;border:1px solid #2c3540;border-radius:8px;padding:10px;height:62vh;
      overflow:auto;font:12px/1.45 ui-monospace,monospace;white-space:pre-wrap}}
 table{{border-collapse:collapse;font-size:12px;width:100%}}
 td,th{{border-bottom:1px solid #2c3540;padding:3px 6px;text-align:right}}
 th:first-child,td:first-child{{text-align:left}}
 .nota{{font-size:11px;color:#7d8894;margin-top:4px}}
</style></head><body>
<header><h1>Banco TFG &middot; CV32E40P / PULPissimo</h1>
 <span id="dot"></span><span id="quehace" style="font-size:13px;color:#9fb0c0">inactivo</span>
 <span style="flex:1"></span>
 <button id="btnstop" class="rojo" disabled onclick="detener()">Detener</button></header>
<main><div>

<div class="card"><h2>Caracterizar &mdash; M1 (bucles)</h2>
 <div>{chk(CATS, "m1cat")}</div>
 <div class="fila">repeticiones <input type="number" id="m1rep" value="1" min="1" max="30" style="width:52px">
  <label class="chip"><input type="checkbox" id="m1nb">no recompilar</label>
  <button onclick="m1()">Caracterizar M1</button></div>
 <div class="nota">~15 min con todas las categorias (reps=1)</div></div>

<div class="card"><h2>Caracterizar &mdash; M2 (regresion)</h2>
 <div class="fila">modelo <select id="m2mod"><option value="efimon" selected>efimon (oficial)</option>
  <option value="clasico">clasico</option><option value="diferencial">diferencial</option></select>
  campanas <input type="number" id="m2n" value="1" min="1" max="10" style="width:52px">
  <label class="chip"><input type="checkbox" id="m2nb">no recompilar</label></div>
 <details><summary style="font-size:12px;cursor:pointer;color:#9fb0c0">programas (15)</summary>
  <div>{chk(PROGS_M2, "m2prog")}</div></details>
 <div class="fila"><button onclick="m2(false)">Caracterizar M2</button>
  <button onclick="m2(true)" style="background:#3a4a5c">Solo re-ajuste (sin banco)</button></div>
 <div class="nota">efimon: 15 programas &times; 3 intensidades + idle &asymp; 30 min por campana.
  Con campanas &gt; 1 se corren en secuencia (reproducibilidad); analizar luego con
  el boton Reproducibilidad.</div></div>

<div class="card"><h2>Verificar (benchmarks)</h2>
 <div class="fila">metodo <select id="vmet"><option value="regresion">M2 regresion</option>
  <option value="bucles">M1 bucles</option></select>
  linea base <select id="vpidle"><option value="temp" selected>temp (corregida)</option>
  <option value="medir">medir ahora</option><option value="archivo">archivo</option></select></div>
 <div>{chk(bm, "vprog")}</div>
 <div class="fila"><button onclick="verificar()">Verificar</button>
  <button onclick="marcar('vprog',true)" style="background:#3a4a5c">todos</button>
  <button onclick="marcar('vprog',false)" style="background:#3a4a5c">ninguno</button></div></div>

<div class="card"><h2>Analisis</h2>
 <div class="fila"><button onclick="lanzar({{accion:'pares'}})">Pares diferenciales</button>
  <button onclick="lanzar({{accion:'repro'}})" style="background:#3a4a5c">Reproducibilidad (sin banco)</button></div></div>

<div class="card"><h2>Estado</h2><div id="estado">cargando...</div></div>

</div><div>
 <div class="card" style="margin-bottom:0"><h2>Consola</h2><div id="log"></div></div>
</div></main>
<script>
let n=0, activo=false, timer=null;
const $=id=>document.getElementById(id);
const sel=g=>[...document.querySelectorAll(`input[name=${{g}}]:checked`)].map(e=>e.value);
function marcar(g,v){{document.querySelectorAll(`input[name=${{g}}]`).forEach(e=>e.checked=v)}}
function programar(ms){{clearTimeout(timer); timer=setTimeout(sondear,ms)}}
async function lanzar(req){{
 const r=await fetch('/run',{{method:'POST',body:JSON.stringify(req)}});
 const j=await r.json();
 if(!j.ok) alert(j.msg); else {{n=0;$('log').textContent='';}}
 programar(100);   // UN solo lazo de sondeo (dos en paralelo duplican lineas)
}}
function m1(){{lanzar({{accion:'m1',cats:sel('m1cat'),repeats:+$('m1rep').value,nobuild:$('m1nb').checked}})}}
function m2(refit){{lanzar({{accion:'m2',modelo:$('m2mod').value,progs:sel('m2prog'),
 campanas:refit?1:+$('m2n').value,refit:refit,nobuild:refit||$('m2nb').checked}})}}
function verificar(){{lanzar({{accion:'verificar',metodo:$('vmet').value,
 pidle:$('vpidle').value,progs:sel('vprog')}})}}
async function detener(){{await fetch('/stop',{{method:'POST'}})}}
async function sondear(){{
 const j=await (await fetch('/log?desde='+n)).json();
 if(j.lineas.length){{const L=$('log');L.textContent+=j.lineas.join('\\n')+'\\n';
  n=j.n; L.scrollTop=L.scrollHeight;}}
 activo=j.corriendo;
 $('dot').className=activo?'on':''; $('btnstop').disabled=!activo;
 $('quehace').textContent=activo?j.nombre+' ('+j.min+' min)':'inactivo';
 programar(activo?700:2500);
 if(!activo) refrescarEstado();
}}
let ultEstado=0;
async function refrescarEstado(){{
 if(Date.now()-ultEstado<5000) return; ultEstado=Date.now();
 const e=await (await fetch('/estado')).json();
 let h='';
 for(const met of ['bucles','regresion']){{const c=e.coef[met]; if(!c) continue;
  h+=`<b>${{met}}</b> <span class="nota">(${{c.fecha||''}})</span><table><tr>`;
  h+=['alu','mul','mulh','div','mem','ctrl','float'].map(k=>`<th>${{k}}</th>`).join('');
  h+='</tr><tr>'+['alu','mul','mulh','div','mem','ctrl','float']
     .map(k=>`<td>${{c[k]??'--'}}</td>`).join('')+'</tr></table>';
  h+=`<div class="nota">P_idle = ${{c.P_idle_W}} W &middot; coef en nJ</div>`;}}
 if(e.valid.length){{h+='<b>ultimas validaciones</b><table><tr><th>fecha</th><th>met</th><th>prog</th><th>err%</th></tr>';
  for(const v of e.valid) h+=`<tr><td>${{v.fecha}}</td><td>${{v.metodo}}</td><td>${{v.programa}}</td><td>${{v.err_pct}}</td></tr>`;
  h+='</table>';}}
 $('estado').innerHTML=h||'sin datos aun';
}}
sondear();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            b = pagina().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif u.path == "/log":
            desde = 0
            for kv in u.query.split("&"):
                if kv.startswith("desde="):
                    desde = int(kv[6:])
            mins = f"{(time.time()-JOB.inicio)/60:.1f}" if JOB.inicio else "0"
            self._json({"lineas": JOB.log[desde:], "n": len(JOB.log),
                        "corriendo": bool(JOB.corriendo_o_encolado()),
                        "nombre": JOB.nombre, "min": mins})
        elif u.path == "/estado":
            self._json(estado())
        else:
            self._json({"err": "no encontrado"}, 404)

    def do_POST(self):
        cuerpo = self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0)
        if self.path == "/run":
            try:
                nombre, cmd = cmd_de(json.loads(cuerpo or b"{}"))
            except (ValueError, json.JSONDecodeError) as e:
                return self._json({"ok": False, "msg": str(e)})
            ok, msg = JOB.lanzar(nombre, cmd)
            self._json({"ok": ok, "msg": msg})
        elif self.path == "/stop":
            self._json({"ok": JOB.detener()})
        else:
            self._json({"err": "no encontrado"}, 404)


if __name__ == "__main__":
    lan = "--lan" in sys.argv
    if "--puerto" in sys.argv:
        PORT = int(sys.argv[sys.argv.index("--puerto") + 1])
    srv = ThreadingHTTPServer(("0.0.0.0" if lan else "127.0.0.1", PORT), H)
    print(f"GUI del banco: http://localhost:{PORT}   (Ctrl-C para salir)")
    if lan:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))          # no manda nada; solo resuelve la IP local
            print(f"  desde el telefono (misma WiFi): http://{s.getsockname()[0]}:{PORT}")
        finally:
            s.close()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        JOB.detener()
