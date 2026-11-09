"""Interfaz con checkers testlib. No interpreta aceptación como equivalencia."""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent
WORKER = BASE / 'checker_contenedor.py'
TEMPORALES = BASE / '.temporales'


def verificar(checker, testlib, entrada, original, propuesta, imagen=None):
    checker, testlib = Path(checker).resolve(), Path(testlib).resolve()
    imagen = imagen or os.environ.get('TESIS_DOCKER_IMAGE', 'tesis-checker:local')
    inicio = time.perf_counter()
    TEMPORALES.mkdir(exist_ok=True)
    nombre = 'tesis-checker-' + uuid.uuid4().hex
    try:
        with tempfile.TemporaryDirectory(prefix='checker_', dir=TEMPORALES) as tmp:
            fuentes = Path(tmp)
            shutil.copyfile(checker, fuentes / 'checker.cpp')
            shutil.copyfile(testlib, fuentes / 'testlib.h')
            huellas = {'checker_sha256': hashlib.sha256((fuentes / 'checker.cpp').read_bytes()).hexdigest(),
                       'testlib_sha256': hashlib.sha256((fuentes / 'testlib.h').read_bytes()).hexdigest()}
            cmd = ['docker', 'run', '--rm', '-i', '--name', nombre, '--network', 'none', '--read-only',
                   '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--user', '65534:65534',
                   '--pids-limit', '64', '--memory', '384m', '--cpus', '1',
                   '--tmpfs', '/tmp:rw,exec,nosuid,nodev,size=128m',
                   '--mount', f'type=bind,source={fuentes},target=/fuentes,readonly',
                   '--mount', f'type=bind,source={WORKER},target=/worker.py,readonly',
                   '--entrypoint', 'python', imagen, '/worker.py']
            payload = {k: base64.b64encode(v).decode('ascii') for k, v in
                       [('entrada', entrada), ('original', original), ('propuesta', propuesta)]}
            p = subprocess.run(cmd, input=json.dumps(payload).encode('utf-8'), capture_output=True, timeout=110)
            if p.returncode:
                resultado = {'estado': 'fallo_contenedor', 'detalle': p.stderr.decode('utf-8', 'replace')[:2000]}
            else:
                resultado = json.loads(p.stdout)
            resultado.update(huellas)
    except subprocess.TimeoutExpired:
        try:
            limpieza = subprocess.run(['docker', 'rm', '--force', nombre], capture_output=True, text=True, timeout=20)
            detalle = {'codigo': limpieza.returncode, 'diagnostico': limpieza.stderr[:500]}
        except (OSError, subprocess.TimeoutExpired) as error:
            detalle = {'error': str(error)}
        resultado = {'estado': 'tiempo_agotado_contenedor', 'limpieza': detalle}
    except (OSError, json.JSONDecodeError, ValueError) as error:
        resultado = {'estado': 'fallo_infraestructura', 'detalle': str(error)}
    resultado.update({'imagen': imagen, 'segundos_totales': time.perf_counter() - inicio})
    return resultado
