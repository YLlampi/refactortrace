"""Ejecuta un único programa en el contenedor y devuelve un resultado estructurado."""
import base64
import dis
import json
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

MAX_SALIDA = 1_000_000


def obtener_lineas_ejecutables():
    lineas = set()
    def visitar(codigo):
        lineas.update(n for _, n in dis.findlinestarts(codigo) if n > 0)
        for constante in codigo.co_consts:
            if isinstance(constante, types.CodeType):
                visitar(constante)
    try:
        fuente = Path('/programa/programa.py').read_bytes()
        visitar(compile(fuente, '/programa/programa.py', 'exec'))
        return sorted(lineas)
    except (OSError, SyntaxError, ValueError, UnicodeError, OverflowError):
        return None


def main():
    solicitud = json.load(sys.stdin)
    entrada = base64.b64decode(solicitud['entrada'], validate=True)
    limite = float(solicitud['timeout'])
    cobertura = bool(solicitud['cobertura'])
    archivo_cobertura = Path('/tmp/lineas.json')
    cmd = [sys.executable, '-I', '-B']
    if cobertura:
        cmd += ['/control/traza.py', '/programa/programa.py', str(archivo_cobertura)]
    else:
        cmd += ['/programa/programa.py']
    inicio = time.monotonic()
    resultado = {'estado': 'error_entorno', 'codigo_salida': None,
                 'stdout_hex': '', 'stderr_hex': '', 'lineas': [],
                 'lineas_ejecutables': obtener_lineas_ejecutables(),
                 'python_contenedor': sys.version.split()[0]}
    with tempfile.TemporaryFile(dir='/tmp') as salida, tempfile.TemporaryFile(dir='/tmp') as errores:
        try:
            p = subprocess.run(cmd, input=entrada, stdout=salida, stderr=errores,
                               cwd='/tmp', timeout=limite)
            resultado['codigo_salida'] = p.returncode
            resultado['estado'] = 'ok' if p.returncode == 0 else 'error_programa'
            if salida.tell() > MAX_SALIDA or errores.tell() > MAX_SALIDA:
                resultado['estado'] = 'salida_excesiva'
            else:
                salida.seek(0)
                errores.seek(0)
                resultado['stdout_hex'] = salida.read().hex()
                resultado['stderr_hex'] = errores.read().hex()
            if cobertura and resultado['estado'] == 'ok':
                try:
                    lineas = json.loads(archivo_cobertura.read_text(encoding='utf-8'))
                    if not isinstance(lineas, list) or any(type(x) is not int or x < 1 for x in lineas):
                        raise ValueError('Cobertura inválida')
                    resultado['lineas'] = sorted(set(lineas))
                except (OSError, ValueError, TypeError):
                    resultado['estado'] = 'error_cobertura'
        except subprocess.TimeoutExpired:
            resultado['estado'] = 'tiempo_agotado'
        except OSError as error:
            resultado['detalle'] = str(error)
    # Incluye análisis estático, ejecución y lectura de salidas, sin arranque de Docker.
    resultado['segundos_internos'] = time.monotonic() - inicio
    print(json.dumps(resultado, ensure_ascii=False))


if __name__ == '__main__':
    main()
