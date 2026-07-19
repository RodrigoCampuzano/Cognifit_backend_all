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

**21 ejercicios, 92 preguntas: 7 por cada grado del ciclo alto.** Cada grado
cubre siete habilidades distintas, sin repetir ninguna.

### 4º — comprensión literal

| Ejercicio | Habilidad |
|---|---|
| `COMP4_literal_N1` | localizar información explícita |
| `COMP4_verdadero_falso_N1` | contrastar afirmaciones con el texto |
| `COMP4_secuencia_N1` | ordenar los hechos en el tiempo |
| `COMP4_referente_N1` | a quién sustituye cada pronombre |
| `COMP4_homofonos_N1` | hola/ola, tubo/tuvo según el sentido |
| `COMP4_coherencia_N1` | encontrar la frase que no encaja |
| `COMP4_lectura_cronometrada_N1` | lectura silenciosa + comprensión |

### 5º — comprensión inferencial

| Ejercicio | Habilidad |
|---|---|
| `COMP5_inferir_causa_N1` | deducir causas no escritas |
| `COMP5_predecir_final_N1` | anticipar a partir de pistas |
| `COMP5_idea_principal_N1` | idea principal frente a detalle |
| `COMP5_lenguaje_figurado_N1` | refranes y frases figuradas |
| `COMP5_hecho_opinion_N1` | distinguir lo comprobable de lo opinable |
| `COMP5_mejor_resumen_N1` | elegir el resumen que no se queda corto |
| `COMP5_vocabulario_contexto_N1` | deducir palabras por contexto |

### 6º — comprensión crítica y metacognición

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
de intervención lo cubría. La cobertura del ciclo alto pasó de 6 ejercicios en
total (4º: 4, 5º: 2, 6º: 0) a 27 sumando las dos vías.

La progresión es deliberada: 4º localiza lo que está escrito, 5º deduce lo que
no está, 6º evalúa lo que se dice y cómo se dice. Un alumno que no resuelve el
nivel literal no va a resolver el inferencial, así que conviene no saltárselo
aunque le corresponda por edad.

En `verificar_afirmaciones` las opciones son tres a propósito. Un verdadero/falso
deja pasar la confusión que más importa en lectura crítica: distinguir lo que el
texto contradice de aquello sobre lo que simplemente no dice nada.

## Origen del contenido

Textos **originales**, escritos para este banco. No se copió material de Aula PT,
Edufichas ni bancos similares: son gratuitos para uso docente, pero eso no
autoriza a redistribuirlos dentro de una app. Se siguió el criterio de usar esos
bancos como referencia de mecánica, no de archivo.

Los temas se anclaron en contextos del sureste (café, meliponicultura, ámbar de
Simojovel, achiote, regiones del estado, almácigos, historia maya) mezclados con
otros de alcance general (tortugas marinas, colibríes, murciélagos), buscando
que resulten reconocibles sin volverse folclóricos.

Las situaciones cotidianas —el mercado, el camión que se va, el patio de tierra
de la escuela— se escribieron sin marcas de clase social ni de ciudad, porque un
alumno que no se reconoce en el texto lee peor.

## Lo que un especialista tiene que revisar

1. ~~Las metas de palabras por minuto~~ — **resuelto**. Ver la sección
   *Velocidad de lectura* más abajo.
2. **El anclaje cultural.** Los textos suenan plausibles, pero quien escribe no
   conoce Chiapas de primera mano. Conviene que un docente de la región revise
   vocabulario y contextos.
3. **La dificultad del léxico** (sedimentos, pendiente, jobones, meliponas). Las
   palabras técnicas están explicadas en contexto, pero merece criterio.
4. **La longitud de los textos** (51 a 160 palabras, creciendo con el grado).
   El PDF de referencia sugiere 80-120 para 4º, que es donde caen los de 4º;
   para 5º y 6º no hay una guía equivalente.

## Velocidad de lectura: el estándar SEP

Los **Estándares Nacionales de Habilidad Lectora** de la SEP fijan, por grado,
las palabras por minuto esperadas **en lectura en voz alta**:

| Grado | ppm | | Grado | ppm |
|---|---|---|---|---|
| 1º | 35–59 | | 4º | 100–114 |
| 2º | 60–84 | | 5º | 115–124 |
| 3º | 85–99 | | 6º | 125–134 |

Fuente: <https://www.gob.mx/sep/acciones-y-programas/estandares-nacionales-de-habilidad-lectora-habilidad-lectora>

**El estándar es oral y estos dos ejercicios son de lectura silenciosa**, que es
más rápida. Por eso no se usa como meta sino como **piso**: quien lee en silencio
por debajo del mínimo oral de su grado va lento con seguridad. Los ejercicios
llevan `meta_es_piso: true` y `meta_fuente` con la cita.

Las metas anteriores (115 en 4º, 135 en 6º) eran inventadas y quedaban justo
arriba de la banda oral de cada grado — sin nada que las sustentara.

### Lo que apareció al contrastar el banco de intervención

Tres ejercicios de fluidez tienen metas **por debajo del mínimo nacional** de los
grados que declaran cubrir:

| Ejercicio | Meta | Queda bajo el estándar de |
|---|---|---|
| `LEC_guiada_N1` | 40 | 2º |
| `LEC_temporizador_N1` | 40 | 2º, 3º |
| `LEC_temporizador_N2` | 70 | 3º, 4º, 5º |

**No se cambiaron**: bajar o subir un objetivo remedial es criterio clínico. Un
hito de 70 ppm para un alumno de 5º con dificultad severa puede ser correcto como
paso intermedio.

Lo que sí es un problema hoy: `ReadingPlayer` calcula `accuracy = ppm / meta` con
tope 1.0, así que ese alumno obtiene **1.0 y la ruta lo sube de nivel** sin que
nada indique la distancia hasta el estándar de su grado. Los ejercicios quedaron
anotados con `sep_estandar_por_grado`, `meta_bajo_estandar_sep` y `revisar_meta`
para que la decisión se tome con el dato a la vista.

## Cómo agregar más grados

Basta con añadir ejercicios al JSON con el `grados` correspondiente: el índice
por grado se arma solo al arrancar y `/comprehension/{grade}` los expone sin
tocar código.

Los ids deben ser únicos **entre los dos bancos** — si se repite uno, el servicio
falla al arrancar en vez de que `/exercises/{id}` devuelva el ejercicio
equivocado en silencio.

El ciclo alto (4º-6º) está cubierto. Lo que sigue, si se quiere extender, es
1º-3º — pero ahí el banco de intervención ya tiene 67 ejercicios y la prioridad
es menor.

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
