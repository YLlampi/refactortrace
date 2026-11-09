# Comprobación de generadores y validadores de LintEval

> Nota de publicación: las copias de datos, el caso exploratorio y sus informes individuales son locales y no se incluyen en el repositorio. El README principal explica cómo descargar los archivos y ejecutar la auditoría actual de desarrollo.

Fecha: 8 de noviembre de 2026. Comprobación exploratoria; no constituye el piloto completo ni una medición del aporte de la tesis.

## Datos y entorno

Se descargó [LintEval Lite JSONL](https://github.com/6643789wsx/LintEval/blob/master/lite/linteval_lite.jsonl) a `linteval_lite.jsonl`. SHA-256: `4d7143ca984022e496b343dbffaa769ac99c35cb32fa45bd9e8c0151a00d7c06`. Hay 498 registros, 203 de ellos Python correspondientes a 203 identificadores de problema distintos. Los 203 tienen campos no vacíos para código, generador, comandos, validador y checker; 201 incluyen revisión publicada. Un campo no vacío no demuestra que funcione.

Se usó [testlib.h de LintEval](https://github.com/6643789wsx/LintEval/blob/master/tools/testlib.h), SHA-256 `bb323e3c89285214966076e0d23d5a295c5f6126da7ff198c1276ddb95ecb1a0`. Se compilaron y ejecutaron generador y validador C++ en contenedores Docker sin red, con código fuente montado en solo lectura, sin capacidades adicionales y con límites de memoria, CPU y procesos. Se utilizó la imagen local `ewayra-f2-build-input:py3144`, ID `sha256:fd8d3d1c021fa451d07f99009e759e39c70df6b8db0a63c379c7bc6743e07362`, y g++ 14.2.0. La imagen es local a este equipo; para reproducir en otro se debe preparar y fijar una imagen equivalente.

## Resultados

Para cada comando seleccionado se ejecutó dos veces el generador y se comparó la salida. La primera salida fue comprobada con el validador oficial. La cantidad de entradas distintas se calculó por SHA-256 de los bytes.

| Problema Python | Comandos probados | Salidas aceptadas | Entradas aceptadas distintas | Salidas repetibles |
|---|---:|---:|---:|---:|
| `p00364_py3_0` | Los 32 publicados | 30 | 29 | 32 |
| `p02553_py3_0` | Primeros 8 comandos distintos | 8 | 8 | 8 |
| `1089_G_py3_0` | Primeros 8 comandos distintos | 8 | 8 | 8 |

En `p00364`, las ocho entradas manuales también fueron aceptadas por el validador oficial. Los dos comandos rechazados pasan `-t 100001`; el validador informa que el límite máximo es `100000`. No se modificaron esos comandos ni se usaron sus salidas. De los 30 resultados aceptados, dos son iguales, por eso hay 29 entradas distintas. Los resultados repetibles corresponden a repetir **el mismo comando**, no a una evaluación de la variedad de semillas.

Los otros dos problemas se seleccionaron por orden de aparición, no mediante muestreo representativo; solo se probaron ocho comandos distintos en cada uno. Que estos hayan funcionado no implica que todos los comandos o muestras funcionen. La salida y los diagnósticos de cada ejecución se guardaron en `auditoria_generador.json` dentro de la carpeta correspondiente.

## Uso con el prototipo

Para `p00364` se seleccionaron las primeras 20 entradas distintas aceptadas por el validador. `seleccionar_generadas.py` reproduce la selección y guarda para cada entrada su comando y hash. Los casos `caso_revision_generadas.json` y `caso_control_generadas.json` contienen las mismas entradas.

Con la estrategia de cambios, la revisión publicada no mostró diferencias en las 20 entradas; la versión con un error deliberado produjo una diferencia reproducida en `g01`. Los informes están en `informe_revision_generadas.json` e `informe_control_generadas.json`. El primer resultado no demuestra equivalencia y el segundo es un control artificial, no una regresión descubierta en LintEval. La ejecución del prototipo no se hizo dentro del contenedor de la auditoría; se utilizaron programas pequeños revisados previamente.

## Límites y pasos siguientes

- Auditar más problemas y seleccionar una muestra de desarrollo con criterios definidos; no extrapolar estos tres casos a las 203 muestras.
- Automatizar la preparación por problema, registrar las exclusiones y separar por problema los conjuntos de desarrollo y evaluación. Reservar entradas finales independientes sin usarlas en correcciones.
- Verificar los checkers originales y adaptar la comparación para problemas que no emplean coincidencia exacta o tolerancia numérica simple.
- Completar el aislamiento para ejecutar código de muestras y propuestas; el ejecutor actual solo limita tiempo y usa procesos separados.
- Contabilizar generación, validación y otros costos en la evaluación. Los tiempos de las ejecuciones exploratorias no son una comparación justa de eficiencia.

## Repetir el primer caso

Desde la raíz de la tesis, con Docker disponible y la imagen indicada:

```powershell
python prototipo_refactorizacion/ejemplos/linteval_p00364/ejecutar_auditoria.py
python prototipo_refactorizacion/ejemplos/linteval_p00364/seleccionar_generadas.py
python prototipo_refactorizacion/prototipo.py prototipo_refactorizacion/ejemplos/linteval_p00364/caso_revision_generadas.json --estrategia cambios --limite 20
python prototipo_refactorizacion/prototipo.py prototipo_refactorizacion/ejemplos/linteval_p00364/caso_control_generadas.json --estrategia cambios --limite 20
```
