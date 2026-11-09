import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / 'piloto'))
import preparar_piloto
import revisar_checkers


class PruebasParticion(unittest.TestCase):
    def test_separacion_de_entradas_es_reproducible_y_disjunta(self):
        entradas = [{'id': str(i), 'sha256': str(i)} for i in range(10)]
        a, b = revisar_checkers.separar(entradas, 'problema')
        self.assertEqual((a, b), revisar_checkers.separar(list(reversed(entradas)), 'problema'))
        self.assertEqual((len(a), len(b)), (7, 3))
        self.assertFalse({x['sha256'] for x in a} & {x['sha256'] for x in b})
        with self.assertRaises(ValueError):
            revisar_checkers.separar(entradas[:4], 'problema')
        with self.assertRaises(ValueError):
            revisar_checkers.separar(entradas[:5] + entradas[:1], 'problema')

    def test_particion_es_reproducible_y_agrupa_por_problema(self):
        filas = [{'language': 'py3', 'problem_id': 'p%03d' % i,
                  'sample_id': 'muestra_%03d' % i} for i in range(60)]
        filas.append({'language': 'py3', 'problem_id': 'p000', 'sample_id': 'otra_muestra'})
        with patch.object(preparar_piloto, 'registros', return_value=filas), \
             patch.object(preparar_piloto, 'hash_archivo', return_value='hash'), \
             patch.object(preparar_piloto, 'CONOCIDOS', {'p000', 'p001', 'p002'}):
            a = preparar_piloto.crear_plan()
            b = preparar_piloto.crear_plan()
        self.assertEqual(a, b)
        self.assertFalse(set(a['desarrollo']) & set(a['evaluacion_reservada']))
        self.assertTrue({'p000', 'p001', 'p002'} <= set(a['desarrollo']))
        self.assertEqual(len(a['muestras_por_problema']['p000']), 2)
        self.assertTrue(set(a['piloto_desarrollo']) <= set(a['desarrollo']))


if __name__ == '__main__':
    unittest.main()
