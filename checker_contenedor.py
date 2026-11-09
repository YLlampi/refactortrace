"""Ejecuta un checker testlib sobre original y propuesta dentro del contenedor."""
import base64
import json
import subprocess
import sys
import time
from pathlib import Path


def ejecutar(args, timeout):
    inicio = time.perf_counter()
    try:
        p = subprocess.run(args, cwd='/tmp', capture_output=True, timeout=timeout)
        return {'estado': 'terminado', 'codigo': p.returncode,
                'diagnostico': p.stderr.decode('utf-8', 'replace')[:2000],
                'segundos': time.perf_counter() - inicio}
    except subprocess.TimeoutExpired:
        return {'estado': 'tiempo_agotado', 'codigo': None, 'segundos': time.perf_counter() - inicio}


def interpretar(r):
    if r['estado'] != 'terminado':
        return 'inconcluso'
    return {0: 'aceptada', 1: 'rechazada', 2: 'rechazada'}.get(r['codigo'], 'inconcluso')


def main():
    datos = json.load(sys.stdin)
    compilacion = ejecutar(['g++', '-std=c++17', '-O2', '-I/fuentes', '/fuentes/checker.cpp',
                            '-o', '/tmp/checker'], 75)
    informe = {'compilacion': compilacion}
    if compilacion['estado'] != 'terminado' or compilacion['codigo'] != 0:
        informe['estado'] = 'compilacion_fallida'
        print(json.dumps(informe))
        return
    entrada = base64.b64decode(datos['entrada'], validate=True)
    original = base64.b64decode(datos['original'], validate=True)
    propuesta = base64.b64decode(datos['propuesta'], validate=True)
    Path('/tmp/entrada').write_bytes(entrada)
    Path('/tmp/referencia').write_bytes(original)
    for nombre, contenido in [('original', original), ('propuesta', propuesta)]:
        Path('/tmp/obtenida').write_bytes(contenido)
        r = ejecutar(['/tmp/checker', '/tmp/entrada', '/tmp/obtenida', '/tmp/referencia'], 8)
        r['interpretacion'] = interpretar(r)
        informe[nombre] = r
    informe['estado'] = 'completado'
    print(json.dumps(informe))


if __name__ == '__main__':
    main()
