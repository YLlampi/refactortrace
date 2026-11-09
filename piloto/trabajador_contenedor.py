"""Audita un problema de desarrollo dentro de un contenedor sin red."""
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

FUENTE = Path('/caso')
LIMITE_BYTES = 2_000_000
MAX_COMANDOS = 20
MAX_COMPROBACIONES = 5


def ejecutar(args, entrada=None, timeout=8):
    inicio = time.perf_counter()
    # Los archivos temporales limitan la memoria consumida por salidas grandes.
    with tempfile.TemporaryFile(dir='/tmp') as out, tempfile.TemporaryFile(dir='/tmp') as err:
        try:
            p = subprocess.run(args, input=entrada, stdout=out, stderr=err,
                               cwd='/tmp', timeout=timeout)
            codigo, estado = p.returncode, 'terminado'
        except subprocess.TimeoutExpired:
            codigo, estado = None, 'tiempo_agotado'
        except OSError as exc:
            return {'estado': 'error_entorno', 'codigo': None, 'detalle': str(exc),
                    'segundos': time.perf_counter() - inicio}, None
        longitud = out.tell()
        out.seek(0)
        err.seek(0)
        contenido = out.read(LIMITE_BYTES + 1)
        diagnostico = err.read(2000).decode('utf-8', 'replace')
    if longitud > LIMITE_BYTES:
        estado, contenido = 'salida_excesiva', None
    return {'estado': estado, 'codigo': codigo, 'bytes_salida': longitud,
            'stderr': diagnostico, 'segundos': time.perf_counter() - inicio}, contenido


def compilar(nombre, destino):
    return ejecutar(['g++', '-std=c++17', '-O2', '-I/caso', str(FUENTE / nombre),
                     '-o', '/tmp/' + destino], timeout=75)[0]


def correcto(registro):
    return registro['estado'] == 'terminado' and registro['codigo'] == 0


def main():
    inicio = time.perf_counter()
    resultado = {'compilaciones': {}, 'comandos': [], 'entradas': [], 'ejecuciones_original': []}
    for archivo, binario in (('generador.cpp', 'gen'), ('validador.cpp', 'validator')):
        registro = compilar(archivo, binario)
        resultado['compilaciones'][archivo] = registro
        if not correcto(registro):
            resultado['estado'] = 'compilacion_fallida'
            resultado['segundos_totales'] = time.perf_counter() - inicio
            print(json.dumps(resultado, ensure_ascii=False))
            return
    lineas = (FUENTE / 'comandos.txt').read_text(encoding='utf-8').splitlines()
    candidatas = list(dict.fromkeys(x.strip() for x in lineas if x.strip() and not x.strip().startswith('#')))
    resultado['comandos_unicos_disponibles'] = len(candidatas)
    vistos = set()
    for linea in candidatas[:MAX_COMANDOS]:
        try:
            partes = shlex.split(linea)
        except ValueError as exc:
            resultado['comandos'].append({'comando': linea, 'estado': 'formato_no_admitido', 'detalle': str(exc)})
            continue
        if not partes or partes[0] != './gen' or any(any(c in x for c in ';|&<>`$') for x in partes):
            resultado['comandos'].append({'comando': linea, 'estado': 'formato_no_admitido'})
            continue
        args = ['/tmp/gen', *partes[1:]]
        generacion, entrada = ejecutar(args)
        item = {'comando': linea, 'generacion': generacion}
        resultado['comandos'].append(item)
        if not correcto(generacion) or entrada is None:
            item['estado'] = 'generacion_fallida'
            continue
        repeticion, entrada_2 = ejecutar(args)
        item['repeticion'] = repeticion
        if not correcto(repeticion) or entrada != entrada_2:
            item['estado'] = 'generador_no_reproducible'
            continue
        valido, _ = ejecutar(['/tmp/validator'], entrada)
        item['validacion'] = valido
        if not correcto(valido):
            item['estado'] = 'validacion_fallida'
            continue
        digest = hashlib.sha256(entrada).hexdigest()
        item['sha256'] = digest
        if digest in vistos:
            item['estado'] = 'duplicada'
            continue
        try:
            texto = entrada.decode('utf-8')
        except UnicodeDecodeError:
            item['estado'] = 'codificacion_no_admitida'
            continue
        vistos.add(digest)
        item['estado'] = 'aceptada'
        resultado['entradas'].append({'id': 'g%02d' % len(vistos),
                                      'stdin': texto, 'sha256': digest, 'comando': linea,
                                      'validez': 'revisada'})
    # Comprobar determinismo y terminación del programa original, sin afirmar corrección.
    for entrada in resultado['entradas'][:MAX_COMPROBACIONES]:
        datos = entrada['stdin'].encode('utf-8')
        primero, salida_1 = ejecutar([sys.executable, '-I', '/caso/original.py'], datos)
        segundo, salida_2 = ejecutar([sys.executable, '-I', '/caso/original.py'], datos)
        resultado['ejecuciones_original'].append({'id': entrada['id'], 'primero': primero,
             'segundo': segundo, 'reproducible': correcto(primero) and correcto(segundo) and salida_1 == salida_2})
    n = len(resultado['entradas'])
    original_ok = len(resultado['ejecuciones_original']) == MAX_COMPROBACIONES and all(
        x['reproducible'] for x in resultado['ejecuciones_original'])
    resultado['estado'] = ('preliminar_apto' if n >= MAX_COMPROBACIONES and original_ok
                           else 'pendiente_insuficiente_o_fallo_original')
    resultado['segundos_totales'] = time.perf_counter() - inicio
    print(json.dumps(resultado, ensure_ascii=False))


if __name__ == '__main__':
    main()
