# RefactorTrace

Prototipo para estudiar si priorizar entradas que alcanzan líneas modificadas ayuda a detectar cambios de comportamiento en programas Python. El proyecto forma parte de una **propuesta de tesis en desarrollo**: todavía no integra un LLM, no verifica el objetivo estructural y no contiene resultados experimentales finales. Las comprobaciones realizadas hasta ahora son exploratorias.

## Inicio rápido

Requisitos: Python 3.10 o posterior. El ejemplo y las pruebas unitarias usan únicamente la biblioteca estándar. Desde la raíz de este repositorio:

```powershell
python prototipo.py ejemplos/valor_absoluto/caso.json --estrategia cambios
python prototipo.py ejemplos/valor_absoluto/caso.json --estrategia general
python prototipo.py ejemplos/valor_absoluto/caso.json --estrategia aleatoria
python -m unittest discover -s . -p 'test_*.py' -v
```

El ejemplo tiene un error deliberado: el original imprime `2` para `-2`, mientras que la versión modificada imprime `-2`. El resultado esperado es `diferencia_reproducida`; esto no constituye una evaluación científica.

## Comparación y checkers

El prototipo ejecuta y compara el programa original y una versión ya escrita. Las estrategias `cambios` y `general` miden cobertura en el original; `aleatoria` compara sin esa preparación. El informe registra ejecuciones, resultados y tiempos. Si encuentra una diferencia, la repite en ambas versiones para comprobar su reproducibilidad.

Opcionalmente puede ejecutar un checker compatible con testlib en Docker, sin red y con recursos limitados:

```powershell
docker build -f Dockerfile.checker -t tesis-checker:local .
python prototipo.py RUTA/caso.json --checker RUTA/checker.cpp --testlib RUTA/testlib.h
```

Puede elegirse otra imagen con `--imagen-checker` o `TESIS_DOCKER_IMAGE`. La imagen debe tener Python y g++. Para un experimento, fije y registre el identificador de la imagen, las herramientas y el entorno.

Cada comparación informa `stdout_identica` y, si se usa checker, los resultados de aceptación del original y la propuesta. El original se proporciona al checker como respuesta de referencia. **La aceptación del checker y la igualdad de salidas son observaciones distintas**: algunos checkers aceptan soluciones diferentes y otros comparan con la respuesta dada; ninguno demuestra equivalencia general. Fallos de compilación, tiempo agotado y errores del contenedor son inconclusos. Compilar el checker en cada comparación agrega costo; el informe lo incluye en su tiempo total, pero no pretende ser una evaluación de eficiencia final.

## Datos de LintEval y piloto

El repositorio no redistribuye los datos descargados de LintEval ni las entradas y fuentes derivadas. Para obtener dos archivos públicos desde sus fuentes oficiales y comprobar sus hashes:

```powershell
python descargar_datos.py
docker build -f Dockerfile.checker -t tesis-checker:local .
python piloto/preparar_piloto.py plan
python piloto/preparar_piloto.py auditar --trabajadores 3
python piloto/revisar_checkers.py --trabajadores 3
```

Las rutas y los hashes descargados están fijados en el script; si los archivos remotos cambian, la descarga se detendrá. Consulte la [procedencia y condiciones de LintEval](https://github.com/6643789wsx/LintEval/blob/master/docs/DATA.md) y de CodeContests antes de usar o redistribuir datos. Los informes derivados se guardan localmente y no se publican por defecto.

Los resultados exploratorios y sus límites están en [generadores](INFORME_GENERADORES.md), [preparación del piloto](piloto/RESULTADOS_PREPARACION.md) y [checkers](piloto/RESULTADOS_CHECKERS.md). Los conjuntos de comprobación interna no son la evaluación final. No se han estudiado los 40 problemas reservados.

## Limitaciones

La selección basada en líneas es aproximada y puede fallar con código reorganizado o solo añadido. Las entradas deben prepararse y validarse con conocimiento de su problema. No se han integrado el modelo de lenguaje, las correcciones automáticas ni la verificación estructural. Los tiempos de ejemplo no prueban ahorros; la generación y validación externas deben contabilizarse antes de comparar métodos.

**Solo el checker se ejecuta en Docker.** Los programas original y modificado se ejecutan en procesos locales, con límite de tiempo, pero sin aislamiento de seguridad: use únicamente código de confianza. Antes de evaluar programas externos, hay que aislar también esas ejecuciones y controlar recursos y procesos hijos.

## Estado de publicación

La configuración de Git excluye datos de terceros, resultados individuales, temporales y archivos de credenciales. Antes de publicar, revise los archivos seleccionados, el contenido de los informes y la licencia que el autor quiera aplicar al código propio. No se ha asignado una licencia al código de este proyecto.
