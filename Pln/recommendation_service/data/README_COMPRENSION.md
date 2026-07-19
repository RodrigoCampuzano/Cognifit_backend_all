# Vía universal de comprensión

**Estado: borrador. `revisado_por_especialista: false` en el JSON. El servicio lo
avisa en cada arranque.**

## Por qué está separada del banco de intervención

Hay dos vías de entrega y no se mezclan:

| Vía | Se entrega por | Archivo |
|---|---|---|
| Intervención | perfil diagnóstico `(subtipo, severidad)` | `banco_ejercicios_intervencion.json` |
| **Comprensión** | **grado** | `banco_comprension_universal.json` |

La razón no es organizativa, es que **el tamizaje no puede detectar dificultades
de comprensión**. `assessment.test_items` es `stimulus_text` + `expected_response`:
mide dictado y lectura a nivel palabra. No tiene estructura de texto + preguntas.

De ahí se sigue todo lo demás:

- Los subtipos que el modelo emite son `fonologico`, `visual`, `mixto`, `fluidez`.
  Ninguno predice comprensión.
- `LEARNING_ROUTES` tiene 12 llaves y ninguna de comprensión.
- El banco usa `perfil_objetivo` ∈ {fonologico, visual, mixto, fluidez}.

Meter los ejercicios de comprensión en `LEARNING_ROUTES` los entregaría según un
perfil que no los predice. Dejarlos en el banco sin ruta los volvería
inalcanzables — es lo que le pasó a `M10_VD` durante meses.

Por eso se entregan por grado, a cualquier alumno, tenga o no perfil de riesgo.

## Lo que reemplaza

`COMP_textos_cortos_N1`, el único ejercicio de comprensión del banco viejo, no
tiene contenido: solo `referencia_banco: "comprension_lectora_CogniFit"`. Ese
banco **no existe** — el string aparece únicamente en el propio ejercicio y en la
migración que lo copia. Era un puntero colgado desde el inicio.

## Contenido actual

7 ejercicios de 6º, 31 preguntas. Cubren los seis focos de comprensión crítica y
metacognición:

| Ejercicio | Habilidad |
|---|---|
| `COMP6_comparar_textos_N1` | contrastar dos textos sobre el mismo tema |
| `COMP6_intencion_autor_N1` | detectar intención y sesgo |
| `COMP6_verificar_afirmaciones_N1` | lo dice / lo contradice / no habla de eso |
| `COMP6_texto_discontinuo_N1` | leer un instructivo |
| `COMP6_organizar_info_N1` | ubicar información en categorías |
| `COMP6_autoevaluacion_N1` | predecir el desempeño y comparar |
| `COMP6_lectura_cronometrada_N1` | lectura silenciosa + comprensión |

Se empezó por 6º porque estaba en **cero absoluto**: ningún ejercicio del banco
de intervención lo cubre (1º: 21, 2º: 27, 3º: 19, 4º: 4, 5º: 2, 6º: 0).

En `verificar_afirmaciones` las opciones son tres a propósito. Un verdadero/falso
deja pasar la confusión que más importa en lectura crítica: distinguir lo que el
texto contradice de aquello sobre lo que simplemente no dice nada.

## Origen del contenido

Textos **originales**, escritos para este banco. No se copió material de Aula PT,
Edufichas ni bancos similares: son gratuitos para uso docente, pero eso no
autoriza a redistribuirlos dentro de una app. Se siguió el criterio de usar esos
bancos como referencia de mecánica, no de archivo.

Los temas se anclaron en contextos de Chiapas (café, meliponicultura, regiones
del estado, almácigos, historia maya) buscando que resulten reconocibles sin
volverse folclóricos.

## Lo que un especialista tiene que revisar

1. **La meta de 135 ppm** de `COMP6_lectura_cronometrada_N1` está marcada con
   `meta_ppm_requiere_validacion: true`. Es lectura *silenciosa*, más rápida que
   la oral, pero no encontré en el repo una fuente normativa para 6º en español
   mexicano. Contrastar contra los estándares de lectura de la SEP.
2. **El anclaje cultural.** Los textos suenan plausibles, pero quien escribe no
   conoce Chiapas de primera mano. Conviene que un docente de la región revise
   vocabulario y contextos.
3. **La dificultad del léxico** (sedimentos, pendiente, jobones, meliponas). Las
   palabras técnicas están explicadas en contexto, pero merece criterio.
4. **La longitud de los textos** (65 a 160 palabras). El PDF de referencia sugiere
   80-120 para 4º; para 6º no hay una guía equivalente.

## Cómo agregar más grados

Basta con añadir ejercicios al JSON con el `grados` correspondiente: el índice
por grado se arma solo al arrancar y `/comprehension/{grade}` los expone sin
tocar código.

Los ids deben ser únicos **entre los dos bancos** — si se repite uno, el servicio
falla al arrancar en vez de que `/exercises/{id}` devuelva el ejercicio
equivocado en silencio.

Siguientes por prioridad: 5º (comprensión inferencial) y 4º (comprensión
literal), en ese orden, porque son el escalón previo al de 6º.

## Cómo se juega

`ComprehensionPlayer` en Flutter. Dos decisiones que conviene no revertir sin
pensarlo:

- **El texto sigue disponible mientras se responde.** Ocultarlo mediría memoria,
  no comprensión — y en un alumno con dificultades lectoras esas dos cosas se
  confunden fácil. Volver al texto a verificar es la estrategia que el ejercicio
  quiere enseñar.
- **La precisión que se reporta es la de las preguntas, no las palabras por
  minuto.** Las ppm viajan como metadato. Reportar velocidad como precisión
  premiaría leer rápido sin entender.
