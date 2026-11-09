# Estado: primera comprobación con LintEval

> Nota de publicación: este informe histórico menciona archivos locales de LintEval que no se incluyen en el repositorio. El README principal explica cómo obtener los datos y repetir las auditorías actuales.

Fecha: 8 de noviembre de 2026. Esta es una comprobación exploratoria de un solo programa, no el piloto completo ni una evaluación de la tesis.

**Actualización posterior:** ya se ejecutaron el generador y el validador oficiales, y se exploraron otros dos problemas. Véase [Informe de generadores](INFORME_GENERADORES.md). Las observaciones siguientes describen la primera etapa, anterior a esa auditoría.

## Fuente y preparación

Se descargó [lite/preview.json](https://github.com/6643789wsx/LintEval/blob/master/lite/preview.json), muestra publicada por los autores. SHA-256 del archivo descargado: `43d819c65da09494029ed1c335e87466f2a81f5a50847c2e12b3db1783f7f065`. Se seleccionó el registro Python `p00364_py3_0`, problema `p00364`, denominado «Bange Hills Tower» en el registro. El archivo local de origen es `linteval_preview.json`; el material de trabajo está en `ejemplos/linteval_p00364/`.

Se extrajeron el programa, la revisión publicada, el generador, sus comandos, el validador y el verificador de salida. La revisión publicada sirve aquí solo para comprobar el funcionamiento de la herramienta; **no es una refactorización generada en este estudio**. También se preparó una versión con un error deliberado como control de detección.

Se escribieron ocho entradas pequeñas a mano. Una comprobación Python independiente aplica los límites y condiciones del validador incluido en el registro: formato, cantidad de líneas, rangos y posiciones diferentes. Todas las entradas pasaron esta comprobación. No se compiló ni ejecutó el validador C++ oficial, así que esta revisión no sustituye su ejecución. No se usaron los generadores ni se probó la producción automática de entradas.

El verificador publicado acepta una diferencia absoluta de hasta `0.001 + 1e-10` para su resultado numérico. El prototipo se amplió para admitir esa tolerancia en este caso, en lugar de comparar los textos literalmente. La implementación local no sustituye una verificación completa con el checker oficial.

## Resultado observado

Se usaron las ocho entradas con límite de ocho comparaciones, semilla 42 y tiempo máximo de 2 segundos por proceso. Los seis informes JSON se encuentran en `ejemplos/linteval_p00364/informes_exploratorios/`.

| Versión modificada | Estrategias | Resultado observado |
|---|---|---|
| Revisión publicada | Cambios, general y aleatoria | Sin diferencias observadas en las ocho entradas. |
| Error deliberado | Cambios y general | Diferencia reproducida con `01_minimo`. |
| Error deliberado | Aleatoria | Diferencia reproducida con `04_pendiente_decreciente`. |

Se aprobaron las seis pruebas automatizadas del prototipo, incluida la comparación numérica con tolerancia. Las ejecuciones corresponden a una muestra y un control artificial: no permiten estimar mejora, ahorro, equivalencia general ni rendimiento en LintEval.

## Hallazgos y pasos pendientes

- El archivo incluye comandos para el generador con `t=100001`, mientras que el validador del mismo registro limita `t` a `100000`. Debe investigarse esta discrepancia antes de usar esas órdenes; no asumir que todo lo generado sea válido.
- Hace falta compilar y ejecutar el validador y el generador oficiales, comprobar la disponibilidad del compilador y `testlib.h`, y determinar si hay suficientes entradas válidas y distintas por problema. También se debe verificar un aislamiento de ejecución apropiado para programas externos.
- Hay que descargar y analizar más muestras de LintEval, separarlas por problema y reservar una evaluación independiente. Ocho entradas manuales y un solo caso no bastan para el piloto de 15–20 casos.
- La implementación aún no valida automáticamente entradas generales ni incorpora LLM, verificación estructural o evaluación final. El costo de creación y validación manual de entradas no figura en los tiempos del prototipo.

## Reproducir

Desde la raíz de la tesis:

```powershell
python prototipo_refactorizacion/ejemplos/linteval_p00364/comprobar_entradas.py
python prototipo_refactorizacion/prototipo.py prototipo_refactorizacion/ejemplos/linteval_p00364/caso_revision.json --estrategia cambios --limite 8
python prototipo_refactorizacion/prototipo.py prototipo_refactorizacion/ejemplos/linteval_p00364/caso_control.json --estrategia cambios --limite 8
python -m unittest discover -s prototipo_refactorizacion -p 'test_*.py' -v
```
