# Propuesta de ejercicios para 4º-6º

**Estado: borrador. Nada de esto se carga en producción hasta que un especialista lo revise.**

## Por qué existe

El banco vigente (`data/banco_ejercicios_intervencion.json`, 29 ejercicios) cubre
bien el ciclo inicial y se queda corto después:

| Grado | Ejercicios hoy |
|---|---|
| 1º | 21 |
| 2º | 27 |
| 3º | 19 |
| 4º | 4 |
| 5º | 2 |
| **6º** | **0** |

Consecuencia real: un alumno de 6º con dislexia severa recibe ejercicios
etiquetados para 1º-2º. El servicio ya lo señala (`grade_appropriate: false` y
un aviso en el mensaje), pero señalarlo no lo resuelve.

## Qué contiene

`ejercicios_4to_6to_PROPUESTA.json` — 13 ejercicios que cubren los 8 tipos del
banco. Si se aprobaran tal cual: 4º pasa de 4 a 13, 5º de 2 a 15 y 6º de 0 a 11.

Sigue exactamente el esquema del banco vigente (mismos campos, mismos códigos de
`perfil_objetivo`), así que puede fusionarse sin tocar código.

## Criterio de diseño

No son los ejercicios de 1º-2º con palabras más largas. En 4º-6º la
decodificación básica ya debería estar automatizada, y lo que persiste es
**fluidez, ortografía arbitraria/morfología y comprensión** — por eso cambia el
objetivo, no solo la dificultad. El vocabulario es del ciclo, no infantilizado:
un alumno de 6º abandona la app si le presentan "sol / luna".

## Lo que un especialista tiene que revisar antes de usarlo

1. **Las metas de palabras por minuto** (90 y 100 ppm) son tentativas. El banco
   actual usa 40 ppm para 1º-2º; no encontré en el repo una fuente normativa para
   el ciclo alto. Hay que contrastarlas contra normas de español mexicano.
2. **Dos ítems son marcadores deliberados** (`CF_sufijos_derivacion_N4` y
   `VIS_ortografia_arbitraria_N3` contienen un ítem con la palabra `REVISAR`).
   Están puestos a propósito para que no se cargue el archivo sin leerlo.
3. **El léxico y los textos** son originales y breves; conviene revisar que sean
   apropiados culturalmente para Chiapas.
4. **La acentuación y las reglas ortográficas** elegidas (b/v, g/j, ll/y, tildes)
   reflejan los focos habituales del ciclo, pero la selección concreta de
   palabras merece criterio clínico.

## Cómo integrarlos (importante)

**El bloqueo de ruteo ya está resuelto.** `build_route()` (en `app/routes.py`)
considera el grado del alumno: cuando la ruta curada de su perfil no tiene
*ningún* ejercicio de su grado —lo que hoy le pasa a todo 4º-6º— completa desde
el banco con los ejercicios del mismo perfil y grado, ordenados por nivel.

Eso significa que **fusionar estos ejercicios basta**: no hay que editar a mano
las doce listas de `LEARNING_ROUTES`. Es también lo que evita repetir el caso
`M10_VD`, que estuvo meses en el banco sin figurar en ninguna ruta.

Medido sobre la propuesta tal como está (perfil fonológico, severidad severa):

| Grado | Hoy | Si se fusiona |
|---|---|---|
| 4º | 8 ejercicios, 0 de su grado | 10 ejercicios, 3 de su grado |
| 5º | 8 ejercicios, 0 de su grado | 10 ejercicios, 4 de su grado |
| 6º | 8 ejercicios, 0 de su grado | 10 ejercicios, 4 de su grado |

Entonces lo que queda es solo contenido:

1. Un especialista revisa y corrige el JSON de propuesta —incluidos los dos
   ítems marcados `REVISAR` a propósito.
2. Se fusionan los ejercicios aprobados en `banco_ejercicios_intervencion.json`.
3. `grade_appropriate` pasa a `true` para 4º, 5º y 6º sin tocar código.

La curaduría de 1º-3º no se ve afectada: si la ruta ya cubre el grado del
alumno, se respeta tal cual y solo se adelantan los ejercicios que le
corresponden.

## Verificación hecha sobre el borrador

- No hay `exercise_id` duplicados contra el banco vigente.
- Todos traen los campos obligatorios del esquema.
- Los `perfil_objetivo` usan solo códigos que `routes.py` ya consume
  (`fonologico`, `visual`, `mixto`, `fluidez`).
