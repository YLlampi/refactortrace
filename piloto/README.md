# Preparación del piloto de LintEval

## Separación de problemas

`preparar_piloto.py plan` crea `particion.json` de manera reproducible a partir de los identificadores de problema y de la semilla indicada. Los tres problemas examinados antes de crear la partición se fuerzan a desarrollo. Los reservados para evaluación no se usan en el lote de desarrollo. La separación no convierte automáticamente sus pruebas en independientes: antes de la evaluación se deben definir y verificar entradas reservadas por separado.

La partición verifica el hash de los datos. Si el archivo de LintEval cambia, el programa se detiene; no reasigna silenciosamente los problemas. La muestra inicial de 20 se elige de desarrollo según el orden aleatorio registrado; no es una muestra representativa garantizada.

## Auditoría de desarrollo

`preparar_piloto.py auditar` prepara únicamente los 20 casos elegidos de desarrollo y los ejecuta en contenedores Docker separados, con red deshabilitada, usuario sin privilegios, sistema de archivos de solo lectura, sin capacidades y con límites de procesos, memoria y tiempo. El uso de Docker requiere que el servicio esté disponible y la imagen local indicada exista. El contenedor tiene acceso de lectura a los archivos de un solo caso, no a la carpeta de evaluación.

En cada caso se compilan el generador y validador oficiales y se prueban como máximo los primeros 20 comandos distintos del archivo. Cada generación se repite, valida y deduplica; solo se aceptan salidas reproducibles y validadas. Después, el original se ejecuta dos veces para las primeras cinco entradas aceptadas. Se guardan los comandos, fallos, resultados, hashes y tiempos en `casos_desarrollo/<problema>/auditoria.json`, además del resumen general.

`preliminar_apto` significa que hubo al menos cinco entradas reproducibles y aceptadas, y que el original terminó con la misma salida en las primeras cinco. **No significa que el caso esté listo para la tesis:** aún faltan revisar el checker y objetivo estructural, la cobertura, el aislamiento de las siguientes etapas y pruebas reservadas. Los demás estados indican problemas o infraestructura pendiente, no una exclusión definitiva.

El tiempo guardado incluye la auditoría en su configuración y concurrencia, no un costo comparable para los métodos de selección. Se limita la cantidad de comandos y el tamaño de cada salida; por ello un caso que produzca pocas entradas aquí podría resultar utilizable con otra preparación documentada.

## Comandos

Desde la raíz del repositorio, después de descargar los datos y construir la imagen descrita en el README principal:

```powershell
python piloto/preparar_piloto.py plan
python piloto/preparar_piloto.py auditar --trabajadores 3
python -m unittest discover -s . -p 'test_*.py' -v
```

El código usa por defecto `tesis-checker:local`, que se puede construir con `Dockerfile.checker`, y admite otra imagen mediante `TESIS_DOCKER_IMAGE`. Las auditorías históricas se realizaron con otra imagen local, cuyo identificador consta en sus informes; no debe asumirse que los tiempos son comparables.

La revisión básica de los checkers y la separación de entradas de desarrollo están documentadas en [RESULTADOS_CHECKERS.md](RESULTADOS_CHECKERS.md). Los archivos de comprobación interna son para desarrollar el prototipo, no constituyen evaluación final.
