"""Primera etapa experimental: ejecución diferencial y priorización de entradas."""
import argparse
import difflib
import dis
import json
import math
import random
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path
import checker as checker_testlib

TRAZA = Path(__file__).with_name('ejecutor_traza.py').resolve()
TEMPORALES = Path(__file__).resolve().parent / '.temporales'


def lineas_ejecutables(codigo):
    resultado = set()
    def visitar(objeto):
        resultado.update(linea for _, linea in dis.findlinestarts(objeto) if linea > 0)
        for constante in objeto.co_consts:
            if isinstance(constante, types.CodeType):
                visitar(constante)
    visitar(compile(codigo, '<codigo>', 'exec'))
    return resultado


def cambios_original(original, modificado):
    a, b = original.splitlines(), modificado.splitlines()
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    cambiadas = set()
    for operacion, inicio, fin, _, _ in matcher.get_opcodes():
        if operacion in ('replace', 'delete'):
            cambiadas.update(range(inicio + 1, fin + 1))
    return cambiadas & lineas_ejecutables(original)


def ejecutar(programa, entrada, limite, cobertura=False):
    inicio = time.perf_counter()
    TEMPORALES.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tesis_ejecucion_', dir=TEMPORALES) as tmp:
        archivo_cobertura = Path(tmp) / 'cobertura.json'
        cmd = [sys.executable, '-I']
        if cobertura:
            cmd += [str(TRAZA), str(programa.resolve()), str(archivo_cobertura)]
        else:
            cmd += [str(programa.resolve())]
        try:
            proceso = subprocess.run(cmd, input=entrada.encode('utf-8'), capture_output=True,
                                    timeout=limite, cwd=tmp)
            estado = 'ok' if proceso.returncode == 0 else 'error_programa'
            lineas = json.loads(archivo_cobertura.read_text(encoding='utf-8')) if archivo_cobertura.exists() else []
            resultado = {'estado': estado, 'codigo_salida': proceso.returncode,
                         'stdout_hex': proceso.stdout.hex(), 'stderr_hex': proceso.stderr.hex(),
                         'lineas': lineas}
        except subprocess.TimeoutExpired:
            resultado = {'estado': 'tiempo_agotado', 'codigo_salida': None,
                         'stdout_hex': '', 'stderr_hex': '', 'lineas': []}
        except OSError as error:
            resultado = {'estado': 'error_entorno', 'detalle': str(error), 'lineas': []}
    resultado['segundos'] = time.perf_counter() - inicio
    return resultado


def ordenar(coberturas, objetivo):
    restantes = set(coberturas)
    cubiertas, orden = set(), []
    while restantes:
        mejor = min(restantes, key=lambda ident: (-len((set(coberturas[ident]) & objetivo) - cubiertas), ident))
        orden.append(mejor)
        cubiertas.update(set(coberturas[mejor]) & objetivo)
        restantes.remove(mejor)
    return orden


def cargar_caso(path):
    caso = json.loads(path.read_text(encoding='utf-8'))
    entradas = caso['entradas']
    ids = [x['id'] for x in entradas]
    if not ids or any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('Las entradas deben tener identificadores únicos y no estar vacías')
    if any(not isinstance(x.get('stdin'), str) or x.get('validez') != 'revisada' for x in entradas):
        raise ValueError('Cada entrada requiere stdin y validez revisada; no se valida automáticamente')
    if len({x['stdin'] for x in entradas}) != len(entradas):
        raise ValueError('Las entradas deben ser distintas')
    return caso


def comparar_salidas(a, b, comparador):
    """Devuelve True/False o None si no se puede interpretar la salida."""
    tipo = comparador.get('tipo', 'exacto')
    if tipo == 'exacto':
        return a == b
    if tipo != 'decimal_tolerancia_absoluta':
        raise ValueError('Comparador desconocido: ' + str(tipo))
    tolerancia = comparador['tolerancia']
    if not isinstance(tolerancia, (int, float)) or not math.isfinite(tolerancia) or tolerancia < 0:
        raise ValueError('Tolerancia inválida')
    try:
        valor_a = float(bytes.fromhex(a).decode('utf-8').strip())
        valor_b = float(bytes.fromhex(b).decode('utf-8').strip())
        if not math.isfinite(valor_a) or not math.isfinite(valor_b):
            return None
        return abs(valor_a - valor_b) <= tolerancia
    except (ValueError, UnicodeError):
        return None


def evaluar(caso_path, estrategia, limite_entradas=5, semilla=42, timeout=2,
            checker_path=None, testlib_path=None, imagen_checker=None):
    if limite_entradas < 1 or timeout <= 0:
        raise ValueError('El límite de entradas y el tiempo deben ser positivos')
    if bool(checker_path) != bool(testlib_path):
        raise ValueError('El checker y testlib.h deben proporcionarse juntos')
    caso = cargar_caso(caso_path)
    comparador = caso.get('comparador', {'tipo': 'exacto'})
    # Comprobar la configuración antes de iniciar cualquier proceso.
    comparar_salidas('30', '30', comparador)
    carpeta = caso_path.parent
    original = (carpeta / caso['original']).resolve()
    modificado = (carpeta / caso['modificado']).resolve()
    codigo_original = original.read_text(encoding='utf-8')
    codigo_modificado = modificado.read_text(encoding='utf-8')
    compile(codigo_modificado, str(modificado), 'exec')
    cambios = cambios_original(codigo_original, codigo_modificado)
    entradas = {x['id']: x['stdin'] for x in caso['entradas']}
    registros = []
    comparaciones = []
    originales = {}
    inicio = time.perf_counter()
    if estrategia in ('cambios', 'general'):
        for ident in sorted(entradas):
            resultado = ejecutar(original, entradas[ident], timeout, cobertura=True)
            originales[ident] = resultado
            registros.append({'entrada': ident, 'version': 'original', 'fase': 'cobertura', **resultado})
        coberturas = {i: r['lineas'] for i, r in originales.items() if r['estado'] == 'ok'}
        objetivo = cambios if estrategia == 'cambios' else lineas_ejecutables(codigo_original)
        orden = ordenar(coberturas, objetivo)
    else:
        orden = sorted(entradas)
        random.Random(semilla).shuffle(orden)
    estado, contraejemplo = 'sin_diferencia_observada', None
    for ident in orden[:limite_entradas]:
        if ident not in originales:
            originales[ident] = ejecutar(original, entradas[ident], timeout)
            registros.append({'entrada': ident, 'version': 'original', 'fase': 'comparacion', **originales[ident]})
        a = originales[ident]
        if a['estado'] != 'ok':
            estado = 'inconcluso'
            continue
        b = ejecutar(modificado, entradas[ident], timeout)
        registros.append({'entrada': ident, 'version': 'modificado', 'fase': 'comparacion', **b})
        if b['estado'] != 'ok':
            estado = 'inconcluso'
            continue
        comparacion_detalle = {'entrada': ident, 'stdout_identica': a['stdout_hex'] == b['stdout_hex']}
        if checker_path:
            comparacion_detalle['checker'] = checker_testlib.verificar(
                checker_path, testlib_path, entradas[ident].encode('utf-8'),
                bytes.fromhex(a['stdout_hex']), bytes.fromhex(b['stdout_hex']), imagen_checker)
        comparaciones.append(comparacion_detalle)
        comparacion = comparar_salidas(a['stdout_hex'], b['stdout_hex'], comparador)
        if comparacion is None:
            estado = 'inconcluso'
            continue
        if not comparacion:
            # Una diferencia debe reproducirse en ambas versiones sin instrumentación.
            rep_a = ejecutar(original, entradas[ident], timeout)
            rep_b = ejecutar(modificado, entradas[ident], timeout)
            registros += [{'entrada': ident, 'version': 'original', 'fase': 'repeticion', **rep_a},
                          {'entrada': ident, 'version': 'modificado', 'fase': 'repeticion', **rep_b}]
            if (rep_a['estado'] == rep_b['estado'] == 'ok' and
                rep_a['stdout_hex'] == a['stdout_hex'] and rep_b['stdout_hex'] == b['stdout_hex']):
                estado, contraejemplo = 'diferencia_reproducida', ident
                break
            estado = 'inconcluso'
    if estrategia != 'aleatoria' and any(r['estado'] != 'ok' for r in originales.values()) and estado != 'diferencia_reproducida':
        estado = 'inconcluso'
    if not orden:
        estado = 'inconcluso'
    return {'caso': caso['id'], 'estrategia': estrategia, 'semilla': semilla,
            'comparador': comparador,
            'limite_entradas': limite_entradas, 'timeout_segundos': timeout,
            'lineas_cambiadas_original': sorted(cambios),
            'seleccion_cambios_aplicable': bool(cambios), 'orden_candidato': orden,
            'estado': estado, 'contraejemplo': contraejemplo, 'ejecuciones': registros,
            'comparaciones': comparaciones,
            'tiempo_total_segundos': time.perf_counter() - inicio}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('caso', type=Path)
    parser.add_argument('--estrategia', choices=['cambios', 'general', 'aleatoria'], default='cambios')
    parser.add_argument('--limite', type=int, default=5)
    parser.add_argument('--semilla', type=int, default=42)
    parser.add_argument('--timeout', type=float, default=2)
    parser.add_argument('--salida', type=Path)
    parser.add_argument('--checker', type=Path, help='Checker testlib del caso')
    parser.add_argument('--testlib', type=Path, help='Archivo testlib.h compatible')
    parser.add_argument('--imagen-checker', help='Imagen Docker con Python y g++')
    args = parser.parse_args()
    informe = evaluar(args.caso.resolve(), args.estrategia, args.limite, args.semilla, args.timeout,
                      args.checker, args.testlib, args.imagen_checker)
    texto = json.dumps(informe, ensure_ascii=False, indent=2)
    if args.salida:
        args.salida.write_text(texto + '\n', encoding='utf-8')
    else:
        print(texto)


if __name__ == '__main__':
    main()
