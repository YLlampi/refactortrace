# Revisión inicial de checkers y separación de entradas

Fecha: 8 de noviembre de 2026. Este trabajo corresponde solo a los 15 problemas **preliminarmente aptos de desarrollo**. No se ejecutaron los 40 problemas reservados para evaluación final y no se llamó a ningún modelo.

**Actualización posterior:** el prototipo ya puede ejecutar opcionalmente un checker testlib en un contenedor y registrar su decisión por separado de la igualdad de salidas. La revisión completa de todos los casos, el aislamiento de los programas y la evaluación final siguen pendientes.

## Qué se hizo

Se revisó el código de los checkers publicados para los 15 problemas. Después se compiló cada checker en Docker aislado y se ejecutaron, como máximo, las primeras 10 entradas aceptadas en la auditoría anterior. Para cada una:

1. Se ejecutó el programa original dos veces y se comprobó que terminara con la misma salida.
2. Se entregó esa salida al checker como salida obtenida y como respuesta de referencia.
3. Se probó también una salida de control malformada. Se consideró superada la comprobación inicial cuando el checker aceptó el original y rechazó el control con código de respuesta de error de salida.

Las entradas y verificadores se ejecutaron en contenedores sin red, con acceso al caso de solo lectura y límites de recursos. Esta es una prueba básica de funcionamiento: no demuestra que el checker sea correcto en general ni que detecte toda diferencia relevante. Se conservan todos los resultados y errores en `casos_desarrollo/<problema>/revision_checker.json`.

## Tipos de checker

| Comportamiento observado en el código | Casos | Implicación |
|---|---:|---|
| Compara secuencias de enteros con la respuesta de referencia | 11 | Hay que seguir las reglas de lectura y comparación del checker; el texto exacto puede diferir solo en formato. |
| Compara secuencias de palabras | 1 | Los espacios de separación no se tratan como una salida de texto exacta. |
| Compara secuencias de decimales con tolerancia | 1 | Hay que aplicar las reglas de tolerancia concretas del checker. |
| Verifica si la solución presentada satisface las condiciones | 2 | Dos salidas diferentes pueden ser aceptadas. Aceptar ambas no demuestra que sean equivalentes ni que el comportamiento original se haya preservado. |

Las categorías se asignaron tras revisar los cinco archivos de checker distintos en estos 15 casos. Falta integrar de forma general los checkers en el prototipo y decidir, antes de la evaluación, cuándo se medirá preservación exacta del comportamiento y cuándo solo validez según el problema. Las dos medidas no deben confundirse. Los checkers oficiales, además, pueden contener errores y necesitan comprobaciones adicionales.

## Resultados observados

Se revisaron 150 entradas: diez por problema. En **146**, el original terminó de forma reproducible, el checker aceptó su salida y rechazó la salida malformada. Las otras cuatro corresponden al problema `1397_C`: el checker rechazó la salida del original para esas entradas. Por ejemplo, informó un índice de operación fuera del rango permitido. Debe revisarse la especificación y el checker antes de atribuir la causa al programa o al conjunto de datos.

Las cuatro entradas rechazadas permanecen en los informes y no se incorporaron a los conjuntos de trabajo de esta comprobación. Este filtrado puede introducir sesgo; no se debe usar para presentar una muestra como representativa o para ocultar fallas del original.

## Separación interna

Las 146 entradas que superaron la comprobación se distribuyeron, por problema, mediante un orden reproducible basado en SHA-256 y la semilla 42:

- **102 entradas para ajuste**, en los 15 problemas.
- **44 entradas para comprobación interna**, en los mismos 15 problemas.

Los archivos se encuentran en cada carpeta como `entradas_ajuste.json` y `entradas_comprobacion_interna.json`. Se comprobó que los hashes no se repitan entre esos dos grupos dentro de cada problema y que correspondan al contenido guardado. Un mismo comando de generación puede producir datos relacionados con otros comandos: entradas distintas y grupos separados **no demuestran independencia estadística**.

Estas entradas se han inspeccionado durante la preparación y pertenecen a problemas de desarrollo. Por eso la comprobación interna sirve para desarrollar el prototipo, **no es la evaluación final reservada**. Los 40 problemas reservados y sus futuras entradas deberán prepararse con reglas fijadas de antemano y mantenerse separados del ajuste de prompts y decisiones del método.

## Próximos pasos

1. Incorporar al prototipo una ejecución aislada de los checkers compatibles y registrar por separado equivalencia observada y validez de la salida.
2. Investigar las cuatro entradas rechazadas de `1397_C` y los cinco problemas pendientes de la auditoría anterior; documentar cualquier exclusión y evitar filtrar según el resultado del método.
3. Preparar el ciclo de refactorización con LLM y verificar el objetivo estructural sin exponer las entradas de comprobación al modelo durante la corrección.
4. Antes de la evaluación final, fijar el protocolo y preparar entradas independientes para los problemas reservados, incluyendo reglas de selección y exclusión y los costos de preparación.

## Reproducir

Con Docker y la imagen local especificada en `README.md`:

```powershell
python prototipo_refactorizacion/piloto/revisar_checkers.py --trabajadores 3
python -m unittest discover -s prototipo_refactorizacion -p 'test_*.py' -v
```

El script no sustituye una partición interna existente si cambian sus entradas: exige revisión manual. Los datos de LintEval y el identificador de la imagen están registrados en los informes anteriores.
