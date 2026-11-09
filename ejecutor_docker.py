"""Ejecuta un archivo Python en Docker con límites y sin red ni montajes de escritura."""
import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent
TEMPORALES = BASE / '.temporales'
TRAZA = BASE / 'ejecutor_traza.py'
WORKER = BASE / 'ejecutor_contenedor.py'
IMAGEN_PREDETERMINADA = 'tesis-checker:local'
MAX_ENTRADA = 2_000_000
ESTADOS = {'ok', 'error_programa', 'tiempo_agotado', 'salida_excesiva', 'error_cobertura', 'error_entorno'}


class LimiteContenedor(Exception):
    def __init__(self, limpieza):
        self.limpieza = limpieza


def detener_contenedor(nombre):
    try:
        limpieza = subprocess.run(['docker', 'rm', '--force', nombre],
                                 capture_output=True, text=True, timeout=20)
        return {'codigo': limpieza.returncode, 'stderr': limpieza.stderr[:500]}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'error': str(error)}


def ejecutar(programa, entrada, limite, cobertura=False, imagen=None):
    inicio = time.perf_counter()
    imagen = imagen or os.environ.get('TESIS_DOCKER_IMAGE', IMAGEN_PREDETERMINADA)
    nombre = 'refactortrace-ejec-' + uuid.uuid4().hex
    entrada_bytes = entrada.encode('utf-8')
    if len(entrada_bytes) > MAX_ENTRADA:
        return {'estado': 'error_entorno', 'detalle': 'La entrada excede el límite permitido',
                'codigo_salida': None, 'stdout_hex': '', 'stderr_hex': '', 'lineas': [],
                'imagen': imagen, 'segundos': time.perf_counter() - inicio}
    solicitud = {'entrada': base64.b64encode(entrada_bytes).decode('ascii'),
                 'timeout': limite, 'cobertura': cobertura}
    try:
        TEMPORALES.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='programa_', dir=TEMPORALES) as tmp:
            carpeta = Path(tmp) / 'programa'
            control = Path(tmp) / 'control'
            carpeta.mkdir()
            control.mkdir()
            (carpeta / 'programa.py').write_bytes(Path(programa).read_bytes())
            shutil.copyfile(TRAZA, control / 'traza.py')
            shutil.copyfile(WORKER, control / 'worker.py')
            cmd = ['docker', 'run', '--rm', '-i', '--pull=never', '--name', nombre,
                   '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                   '--security-opt', 'no-new-privileges', '--user', '65534:65534',
                   '--pids-limit', '32', '--memory', '256m', '--memory-swap', '256m', '--cpus', '1',
                   '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=32m',
                   '--mount', f'type=bind,source={carpeta},target=/programa,readonly',
                   '--mount', f'type=bind,source={control},target=/control,readonly',
                   '--entrypoint', 'python', imagen, '-I', '-B', '/control/worker.py']
            try:
                p = subprocess.run(cmd, input=json.dumps(solicitud).encode('utf-8'),
                                   capture_output=True, timeout=limite + 30)
            except subprocess.TimeoutExpired:
                # Detener primero el contenedor antes de borrar las fuentes montadas.
                raise LimiteContenedor(detener_contenedor(nombre)) from None
        if p.returncode != 0:
            resultado = {'estado': 'error_entorno', 'detalle': p.stderr.decode('utf-8', 'replace')[:2000]}
        else:
            resultado = json.loads(p.stdout)
            if not isinstance(resultado, dict) or resultado.get('estado') not in ESTADOS:
                raise ValueError('Respuesta no válida del ejecutor')
            for campo in ('stdout_hex', 'stderr_hex'):
                valor = resultado.get(campo)
                if not isinstance(valor, str) or len(valor) > 2_000_000:
                    raise ValueError('Salida no válida del ejecutor')
                bytes.fromhex(valor)
            lineas = resultado.get('lineas')
            if not isinstance(lineas, list) or any(type(n) is not int or n < 1 for n in lineas):
                raise ValueError('Cobertura no válida del ejecutor')
            ejecutables = resultado.get('lineas_ejecutables')
            if ejecutables is not None and (not isinstance(ejecutables, list) or
                                            any(type(n) is not int or n < 1 for n in ejecutables)):
                raise ValueError('Líneas ejecutables no válidas')
    except LimiteContenedor as error:
        resultado = {'estado': 'error_entorno', 'detalle': 'Tiempo agotado al iniciar o detener el contenedor',
                     'limpieza': error.limpieza}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        resultado = {'estado': 'error_entorno', 'detalle': str(error)}
    resultado.setdefault('codigo_salida', None)
    resultado.setdefault('stdout_hex', '')
    resultado.setdefault('stderr_hex', '')
    resultado.setdefault('lineas', [])
    resultado.setdefault('lineas_ejecutables', None)
    resultado['imagen'] = imagen
    resultado['segundos'] = time.perf_counter() - inicio
    return resultado
