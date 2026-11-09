# Resultado de la preparación inicial del piloto

Fecha: 8 de noviembre de 2026. Auditoría de viabilidad, no experimento de la tesis.

## Separación

De los 203 problemas Python de LintEval Lite se asignaron 163 a desarrollo y 40 a evaluación reservada mediante el procedimiento reproducible de `particion.json`. Los tres problemas explorados antes de definir la partición se mantienen en desarrollo. La auditoría aquí descrita procesó únicamente 20 problemas seleccionados del grupo de desarrollo. La asignación no demuestra por sí sola que las pruebas finales de cada problema sean independientes; eso sigue pendiente.

## Método de comprobación

Para cada problema se compilaron su generador y validador en Docker sin red. Se intentaron hasta los primeros 20 comandos distintos, repitiendo cada generación y pasando la salida al validador. Se eliminaron entradas duplicadas. En las primeras cinco entradas aceptadas se ejecutó el programa original dos veces, con un máximo de ocho segundos por ejecución, y se compararon las salidas.

Un caso es **preliminarmente apto** si obtiene cinco o más entradas válidas y distintas, y el original termina y produce la misma salida en esas cinco. Este criterio solo sirve para priorizar la preparación posterior. No comprueba que el original sea correcto, que se cumpla una refactorización, ni que el checker pueda integrarse. Tampoco comprueba las entradas aceptadas posteriores a las primeras cinco mediante el original.

## Resultados

- **15 de 20 casos** cumplieron el criterio preliminar.
- **5 de 20 casos** quedaron pendientes. No son exclusiones definitivas: sus causas requieren revisión.
- Se registraron **319 entradas aceptadas y distintas dentro de su propio problema**, sumando los 20 casos, incluidos los pendientes. No se comparó la duplicación entre problemas; no se afirma que todas sean adecuadas para la evaluación final.
- De los comandos probados, 27 tuvieron una salida rechazada por el validador, 12 produjeron una entrada duplicada y 10 tuvieron fallos de generación. Las cifras describen únicamente los comandos examinados, no todos los publicados.

| Caso pendiente | Observación |
|---|---|
| `p02687` | Los tres comandos probados produjeron salidas rechazadas; el validador informó un patrón no admitido. |
| `304_B` | Los 12 comandos probados produjeron salidas rechazadas por el patrón del validador. |
| `p03940` | Se aceptaron 16 entradas, pero el original superó el límite de ocho segundos en dos de las primeras cinco. |
| `603_A` | Se aceptaron 19 entradas; el original terminó con `IndexError` en dos de las primeras cinco. |
| `p03303 SoundHound Inc` | Se aceptaron 20 entradas; el original terminó con `IndexError` en las primeras cinco. |

La aceptación por un validador no demuestra que una entrada cumpla necesariamente la especificación original del problema. Tampoco se ha determinado aún si los errores observados corresponden a entradas inválidas, un defecto del validador, un problema del programa u otra causa.

Los resultados por caso y por comando están en `resumen_auditoria.json` y `casos_desarrollo/<problema>/auditoria.json`. Los valores dependen del límite de comandos, tiempos y recursos registrados en el programa; no son una estimación del porcentaje de casos aptos en todo LintEval.

## Antes de la evaluación

1. Revisar los checkers de los 15 casos preliminares y definir cómo comparar correctamente las salidas de cada problema.
2. Resolver o documentar los cinco casos pendientes con base en la especificación y recursos disponibles, sin cambiar arbitrariamente los criterios para mejorar el resultado.
3. Preparar entradas separadas para la retroalimentación y la evaluación, registrar su procedencia y comprobar que no se filtren al modelo.
4. Integrar el ejecutor del prototipo en un entorno aislado y registrar costos completos, incluidos generación y validación de entradas.
5. Completar la refactorización y el ciclo de corrección con el LLM, y establecer la verificación del objetivo estructural antes del experimento.
