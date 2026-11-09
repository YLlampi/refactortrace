"""Audita checkers en casos de desarrollo y crea conjuntos internos separados."""
import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path

import preparar_piloto as preparacion

BASE = Path(__file__).resolve().parent
TRABAJADOR = BASE / 'revisar_checkers_contenedor.py'
TIPOS = {
    **{x: 'secuencia_enteros' for x in ('690_D3', '937_A', 'p02966', '1046_H', '980_C',
       '604_B', '15_E', 'p00460', '1360_A', 'p01898', '653_C')},
    'p00190': 'secuencia_palabras', '351_B': 'secuencia_decimales',
    '370_D': 'verifica_validez_solucion', '1397_C': 'verifica_validez_solucion',
}


def separar(entradas, problem_id):
    """Orden fijo según hash; no afirma independencia estadística de los datos."""
    if len(entradas) < 5:
        raise ValueError('Se requieren por lo menos cinco entradas comprobadas')
    hashes = [e['sha256'] for e in entradas]
    if len(hashes) != len(set(hashes)):
        raise ValueError('Hay entradas duplicadas')
    def rango(entrada):
        clave = ('42|' + problem_id + '|' + entrada['sha256']).encode('utf-8')
        return hashlib.sha256(clave).hexdigest()
    orden = sorted(entradas, key=rango)
    cuenta = max(2, round(len(orden) * .3))
    return orden[cuenta:], orden[:cuenta]


def ejecutar_auditoria(problem_id, image_id):
    carpeta = BASE / 'casos_desarrollo' / problem_id
    nombre = 'tesis-checker-' + uuid.uuid4().hex
    cmd = ['docker', 'run', '--rm', '--name', nombre, '--label', 'tesis.refactorizacion.checker=true',
           '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
           '--user', '65534:65534', '--pids-limit', '64', '--memory', '384m', '--cpus', '1',
           '--tmpfs', '/tmp:rw,exec,nosuid,nodev,size=128m',
           '--mount', f'type=bind,source={carpeta},target=/caso,readonly',
           '--mount', f'type=bind,source={TRABAJADOR},target=/trabajador.py,readonly',
           '--entrypoint', 'python', preparacion.IMAGEN, '/trabajador.py']
    inicio = time.perf_counter()
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=240)
        informe = json.loads(p.stdout) if p.returncode == 0 else {
            'estado': 'fallo_contenedor', 'detalle': p.stderr.decode('utf-8', 'replace')[:2000]}
    except subprocess.TimeoutExpired:
        try:
            limpieza = subprocess.run(['docker', 'rm', '--force', nombre], capture_output=True, text=True, timeout=20)
            detalle = {'codigo': limpieza.returncode, 'stderr': limpieza.stderr[:500]}
        except (OSError, subprocess.TimeoutExpired) as error:
            detalle = {'error': str(error)}
        informe = {'estado': 'tiempo_agotado_contenedor', 'limpieza': detalle}
    except (OSError, json.JSONDecodeError) as error:
        informe = {'estado': 'fallo_infraestructura', 'detalle': str(error)}
    checker = carpeta / 'checker.cpp'
    informe.update({'problem_id': problem_id, 'tipo_revision_manual': TIPOS.get(problem_id, 'no_revisado'),
                    'checker_sha256': preparacion.hash_archivo(checker), 'imagen_id': image_id,
                    'trabajador_sha256': preparacion.hash_archivo(TRABAJADOR),
                    'segundos_pared': time.perf_counter() - inicio})
    preparacion.guardar_json(carpeta / 'revision_checker.json', informe)
    aceptadas = [x for x in informe.get('revision', []) if x['estado'] == 'comprobacion_inicial_superada']
    return {'problem_id': problem_id, 'tipo': informe['tipo_revision_manual'],
            'estado': informe['estado'], 'evaluadas': len(informe.get('revision', [])),
            'comprobacion_superada': len(aceptadas)}


def generar_particiones(problem_id):
    carpeta = BASE / 'casos_desarrollo' / problem_id
    informe = json.loads((carpeta / 'revision_checker.json').read_text(encoding='utf-8'))
    auditoria = json.loads((carpeta / 'auditoria.json').read_text(encoding='utf-8'))
    superadas = {x['sha256'] for x in informe.get('revision', []) if x['estado'] == 'comprobacion_inicial_superada'}
    entradas = [x for x in auditoria['entradas'] if x['sha256'] in superadas]
    if len(entradas) < 5:
        return {'estado': 'insuficientes_entradas_comprobadas', 'entradas': len(entradas)}
    ajuste, prueba = separar(entradas, problem_id)
    preparado = []
    for nombre, grupo in [('ajuste', ajuste), ('comprobacion_interna', prueba)]:
        destino = carpeta / ('entradas_' + nombre + '.json')
        contenido = {'problem_id': problem_id, 'grupo_problema': 'desarrollo', 'grupo_entradas': nombre,
                     'uso': 'Solo desarrollo; no son pruebas finales de tesis.', 'semilla': 42,
                     'revision_checker_sha256': preparacion.hash_archivo(carpeta / 'revision_checker.json'),
                     'entradas': grupo}
        if destino.exists():
            anterior = json.loads(destino.read_text(encoding='utf-8'))
            if [(x['id'], x['sha256']) for x in anterior['entradas']] != [(x['id'], x['sha256']) for x in grupo]:
                raise ValueError('La partición existente cambiaría; requiere revisión manual: ' + problem_id)
        preparado.append((destino, contenido))
    for destino, contenido in preparado:
        preparacion.guardar_json(destino, contenido)
    return {'estado': 'separadas', 'ajuste': len(ajuste), 'comprobacion_interna': len(prueba)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trabajadores', type=int, default=3, choices=range(1, 5))
    args = parser.parse_args()
    plan = preparacion.leer_plan()
    resumen = json.loads((BASE / 'resumen_auditoria.json').read_text(encoding='utf-8'))
    problemas = [x['problem_id'] for x in resumen['casos'] if x['estado'] == 'preliminar_apto']
    if not set(problemas) <= set(plan['piloto_desarrollo']) or set(problemas) & set(plan['evaluacion_reservada']):
        raise ValueError('Se encontró un caso fuera del desarrollo')
    image_id = subprocess.run(['docker', 'image', 'inspect', preparacion.IMAGEN, '--format', '{{.Id}}'],
                              capture_output=True, text=True, check=True).stdout.strip()
    resultados = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.trabajadores) as pool:
        futuros = {pool.submit(ejecutar_auditoria, p, image_id): p for p in problemas}
        for futuro in concurrent.futures.as_completed(futuros):
            problema = futuros[futuro]
            try:
                item = futuro.result()
                item['particion'] = generar_particiones(problema)
            except Exception as error:
                item = {'problem_id': problema, 'estado': 'fallo_preparacion', 'detalle': str(error)}
            resultados.append(item)
            print(len(resultados), '/', len(problemas), problema, item['estado'],
                  'entradas:', item.get('comprobacion_superada', 0), flush=True)
    resultados.sort(key=lambda x: problemas.index(x['problem_id']))
    preparacion.guardar_json(BASE / 'resumen_checkers.json', {'imagen_id': image_id, 'casos': resultados})


if __name__ == '__main__':
    main()
