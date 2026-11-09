"""Comprueba el checker publicado y el programa original en un contenedor aislado."""
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CASO = Path('/caso')
LIMITE = 2_000_000
MAX_ENTRADAS = 10


def correr(args, entrada=None, timeout=8):
    inicio = time.perf_counter()
    with tempfile.TemporaryFile(dir='/tmp') as salida, tempfile.TemporaryFile(dir='/tmp') as errores:
        try:
            p = subprocess.run(args, input=entrada, stdout=salida, stderr=errores, cwd='/tmp', timeout=timeout)
            estado, codigo = 'terminado', p.returncode
        except subprocess.TimeoutExpired:
            estado, codigo = 'tiempo_agotado', None
        except OSError as exc:
            return {'estado': 'error_entorno', 'codigo': None, 'detalle': str(exc),
                    'segundos': time.perf_counter() - inicio}, None
        longitud = salida.tell()
        salida.seek(0)
        errores.seek(0)
        contenido = salida.read(LIMITE + 1)
        stderr = errores.read(2000).decode('utf-8', 'replace')
    if longitud > LIMITE:
        estado, contenido = 'salida_excesiva', None
    return {'estado': estado, 'codigo': codigo, 'stderr': stderr,
            'segundos': time.perf_counter() - inicio}, contenido


def ok(result):
    return result['estado'] == 'terminado' and result['codigo'] == 0


def main():
    informe = {'revision': [], 'segundos': None}
    inicio = time.perf_counter()
    compilacion, _ = correr(['g++', '-std=c++17', '-O2', '-I/caso', '/caso/checker.cpp',
                              '-o', '/tmp/checker'], timeout=75)
    informe['compilacion'] = compilacion
    if not ok(compilacion):
        informe['estado'] = 'checker_no_compila'
        print(json.dumps(informe, ensure_ascii=False))
        return
    auditoria = json.loads((CASO / 'auditoria.json').read_text(encoding='utf-8'))
    for entrada in auditoria['entradas'][:MAX_ENTRADAS]:
        datos = entrada['stdin'].encode('utf-8')
        uno, out1 = correr([sys.executable, '-I', '/caso/original.py'], datos)
        dos, out2 = correr([sys.executable, '-I', '/caso/original.py'], datos)
        item = {'id': entrada['id'], 'sha256': hashlib.sha256(datos).hexdigest(),
                'original_1': uno, 'original_2': dos}
        informe['revision'].append(item)
        if not ok(uno) or not ok(dos) or out1 != out2:
            item['estado'] = 'original_no_reproducible_o_fallido'
            continue
        Path('/tmp/entrada').write_bytes(datos)
        Path('/tmp/esperada').write_bytes(out1)
        Path('/tmp/obtenida').write_bytes(out1)
        propio, _ = correr(['/tmp/checker', '/tmp/entrada', '/tmp/obtenida', '/tmp/esperada'])
        Path('/tmp/obtenida').write_bytes(b'__SALIDA_INVALIDA__\n')
        invalida, _ = correr(['/tmp/checker', '/tmp/entrada', '/tmp/obtenida', '/tmp/esperada'])
        item['checker_original'] = propio
        item['checker_salida_malformada'] = invalida
        if not ok(propio):
            item['estado'] = 'checker_rechaza_original_o_falla'
        elif invalida['estado'] != 'terminado' or invalida['codigo'] not in (1, 2):
            item['estado'] = 'control_malformado_inconcluso'
        else:
            item['estado'] = 'comprobacion_inicial_superada'
    informe['estado'] = 'completado'
    informe['segundos'] = time.perf_counter() - inicio
    print(json.dumps(informe, ensure_ascii=False))


if __name__ == '__main__':
    main()
