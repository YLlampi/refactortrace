"""Separa problemas y audita casos de desarrollo de LintEval en Docker."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import shutil
import subprocess
import time
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BASE = Path(__file__).resolve().parent
DATOS = RAIZ / 'linteval_lite.jsonl'
TESTLIB = RAIZ / 'ejemplos/linteval_p00364/testlib.h'
TRABAJADOR = BASE / 'trabajador_contenedor.py'
MANIFIESTO = BASE / 'particion.json'
IMAGEN = os.environ.get('TESIS_DOCKER_IMAGE', 'tesis-checker:local')
CONOCIDOS = {'p00364', 'p02553', '1089_G'}
SEMILLA = 42


def hash_archivo(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def registros():
    return [json.loads(linea) for linea in DATOS.read_text(encoding='utf-8').splitlines() if linea.strip()]


def crear_plan():
    filas = [x for x in registros() if x.get('language') == 'py3']
    por_problema = {}
    for fila in filas:
        por_problema.setdefault(fila['problem_id'], []).append(fila['sample_id'])
    if not CONOCIDOS <= set(por_problema):
        raise ValueError('No se encuentran los problemas previamente explorados')
    candidatos = sorted(set(por_problema) - CONOCIDOS)
    random.Random(SEMILLA).shuffle(candidatos)
    reservados = set(candidatos[:40])
    desarrollo = sorted(set(por_problema) - reservados)
    orden = desarrollo.copy()
    random.Random(SEMILLA + 1).shuffle(orden)
    return {'dataset_sha256': hash_archivo(DATOS), 'semilla': SEMILLA,
            'descripcion': 'Separación provisional por problem_id; los tres problemas ya explorados quedan en desarrollo.',
            'seleccion_reserva': 'Primeros 40 problemas tras mezclar con semilla 42; excluye problemas previamente explorados.',
            'seleccion_piloto': 'Primeros 20 de desarrollo tras ordenar y mezclar con semilla 43.',
            'problemas_previamente_explorados': sorted(CONOCIDOS),
            'desarrollo': desarrollo, 'evaluacion_reservada': sorted(reservados),
            'piloto_desarrollo': orden[:20], 'muestras_por_problema': por_problema}


def leer_plan():
    plan = json.loads(MANIFIESTO.read_text(encoding='utf-8'))
    if plan['dataset_sha256'] != hash_archivo(DATOS):
        raise ValueError('El dataset cambió desde la creación de la partición')
    if set(plan['desarrollo']) & set(plan['evaluacion_reservada']):
        raise ValueError('La partición mezcla problemas de desarrollo y evaluación')
    if not set(plan['piloto_desarrollo']) <= set(plan['desarrollo']):
        raise ValueError('El piloto contiene problemas reservados')
    return plan


def guardar_json(path, datos):
    path.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def preparar_caso(fila):
    destino = BASE / 'casos_desarrollo' / fila['problem_id']
    destino.mkdir(parents=True, exist_ok=True)
    for campo, archivo in [('code', 'original.py'), ('generator', 'generador.cpp'),
                           ('validator', 'validador.cpp'), ('generator_cmd', 'comandos.txt'),
                           ('checker', 'checker.cpp')]:
        (destino / archivo).write_text(fila.get(campo) or '', encoding='utf-8', newline='\n')
    shutil.copyfile(TESTLIB, destino / 'testlib.h')
    guardar_json(destino / 'metadatos.json', {'sample_id': fila['sample_id'], 'problem_id': fila['problem_id'],
                 'dataset_sha256': hash_archivo(DATOS), 'testlib_sha256': hash_archivo(TESTLIB),
                 'alertas': fila.get('linter_messages'), 'grupo': 'desarrollo'})
    return destino


def auditar_uno(fila, imagen_id):
    carpeta = preparar_caso(fila)
    inicio = time.perf_counter()
    nombre = 'tesis-refactorizacion-' + uuid.uuid4().hex
    cmd = ['docker', 'run', '--rm', '--name', nombre, '--label', 'tesis.refactorizacion.piloto=true',
           '--network', 'none', '--read-only', '--cap-drop', 'ALL',
           '--security-opt', 'no-new-privileges', '--user', '65534:65534', '--pids-limit', '64',
           '--memory', '384m', '--cpus', '1', '--tmpfs', '/tmp:rw,exec,nosuid,nodev,size=128m',
           '--mount', f'type=bind,source={carpeta},target=/caso,readonly',
           '--mount', f'type=bind,source={TRABAJADOR},target=/trabajador.py,readonly',
           '--entrypoint', 'python', IMAGEN, '/trabajador.py']
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=240)
        if p.returncode:
            informe = {'estado': 'fallo_contenedor', 'detalle': p.stderr.decode('utf-8', 'replace')[:3000]}
        else:
            informe = json.loads(p.stdout)
    except subprocess.TimeoutExpired:
        try:
            limpieza = subprocess.run(['docker', 'rm', '--force', nombre], capture_output=True,
                                     text=True, timeout=20)
            detalle_limpieza = {'codigo': limpieza.returncode, 'stderr': limpieza.stderr[:500]}
        except (subprocess.TimeoutExpired, OSError) as error:
            detalle_limpieza = {'error': str(error)}
        informe = {'estado': 'tiempo_agotado_contenedor', 'limpieza': detalle_limpieza}
    except (OSError, json.JSONDecodeError) as error:
        informe = {'estado': 'fallo_infraestructura', 'detalle': str(error)}
    informe.update({'problem_id': fila['problem_id'], 'sample_id': fila['sample_id'],
                    'imagen_id': imagen_id, 'worker_sha256': hash_archivo(TRABAJADOR),
                    'segundos_pared': time.perf_counter() - inicio})
    guardar_json(carpeta / 'auditoria.json', informe)
    return {'problem_id': fila['problem_id'], 'sample_id': fila['sample_id'],
            'estado': informe['estado'], 'entradas_validas_distintas': len(informe.get('entradas', [])),
            'comandos_probados': len(informe.get('comandos', [])), 'segundos_pared': informe['segundos_pared']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accion', choices=('plan', 'auditar'))
    parser.add_argument('--trabajadores', type=int, default=3, choices=range(1, 5))
    args = parser.parse_args()
    if args.accion == 'plan':
        plan = crear_plan()
        if MANIFIESTO.exists() and json.loads(MANIFIESTO.read_text(encoding='utf-8')) != plan:
            raise SystemExit('Ya existe una partición diferente; no se reemplazará automáticamente.')
        guardar_json(MANIFIESTO, plan)
        print('Partición:', len(plan['desarrollo']), 'desarrollo;', len(plan['evaluacion_reservada']), 'reservados.')
        print('Muestra de desarrollo:', len(plan['piloto_desarrollo']))
        return
    plan = leer_plan()
    imagen_id = subprocess.run(['docker', 'image', 'inspect', IMAGEN, '--format', '{{.Id}}'],
                               capture_output=True, text=True, check=True).stdout.strip()
    filas = {r['problem_id']: r for r in registros()
             if r.get('language') == 'py3' and r.get('problem_id') in plan['piloto_desarrollo']}
    if set(filas) != set(plan['piloto_desarrollo']):
        raise ValueError('Faltan registros del piloto')
    resumen = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.trabajadores) as pool:
        pendientes = {pool.submit(auditar_uno, filas[p], imagen_id): p for p in plan['piloto_desarrollo']}
        for futuro in concurrent.futures.as_completed(pendientes):
            problema = pendientes[futuro]
            try:
                item = futuro.result()
            except Exception as exc:
                item = {'problem_id': problema, 'estado': 'fallo_preparacion', 'detalle': str(exc)}
            resumen.append(item)
            print(len(resumen), '/', len(pendientes), problema, item['estado'],
                  'entradas:', item.get('entradas_validas_distintas', 0), flush=True)
    resumen.sort(key=lambda x: plan['piloto_desarrollo'].index(x['problem_id']))
    guardar_json(BASE / 'resumen_auditoria.json', {'dataset_sha256': plan['dataset_sha256'],
                 'imagen_id': imagen_id, 'casos': resumen})


if __name__ == '__main__':
    main()
