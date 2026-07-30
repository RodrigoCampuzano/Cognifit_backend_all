# Guion del expositor — Minería de datos y PLN

**Duración objetivo:** 15–20 min · 15 diapositivas + 3 de respaldo
**Mazo:** `docs/expo_mineria_pln/index.html` (flechas ← → o barra espaciadora)

> **La tesis del mazo:** el modelo es la última etapa y la más corta. Casi toda
> la señal se decide antes, en qué errores cuentan y cuáles no. Si el jurado se
> lleva una sola idea, que sea esa.
>
> **La regla de honestidad:** todo lo que se afirma está en el repositorio,
> incluidos los tres bugs y el problema del dataset sintético. No se maquilla.

---

## 1 · Portada — 0:30

**Se dice:**
> Este proyecto detecta indicadores de riesgo de dislexia en primaria mexicana.
> Voy a contar cómo se pasa de lo que escribe un niño de siete años a un vector
> de 28 dimensiones, y qué aprendimos al inspeccionar el modelo que salió de ahí.

**No se dice:** nada de arquitectura, Docker ni despliegue. Este mazo es del dato
y el modelo.

---

## 2 · El dato crudo — 1:00

**Se dice:** cada ítem produce cuatro cosas: esperado, producido, tiempo y vía de
entrada. Los cinco módulos.

**Sembrar aquí, cobrar en la 4:**
> Fíjense en `input_method`. Parece un campo administrativo. En dos diapositivas
> va a decidir si un error se corrige o se conserva.

**El punto conceptual:** pseudopalabras contra palabras reales no es una etiqueta
organizativa. Es la comparación que separa un problema fonológico de uno visual:
una pseudopalabra no se puede reconocer de memoria, hay que decodificarla.

---

## 3 · El pipeline — 1:00

**Se dice:** las seis etapas, rápido. No detenerse: es el mapa, no el territorio.

**El remate que enmarca todo el resto:**
> La etapa 3 es la que casi nadie pone en un pipeline de PLN: decidir qué errores
> *no* cuentan. Ahí vive casi toda la lingüística del proyecto, y es de donde
> salieron los hallazgos más interesantes.

---

## 4 · Preprocesamiento — 1:15

**Se dice:** normalización estándar, y luego la corrección de artefactos del
reconocimiento de voz en español mexicano.

**Cobrar la siembra de la 2:**
> Esa corrección se aplicaba mirando solo el módulo. Así que si un niño escribía
> a mano la letra `k` en un dictado, el sistema se la «corregía» a `qu` antes de
> compararla. Estábamos borrando un error real antes de medirlo.
>
> Hoy se condiciona a que la respuesta venga de verdad de un micrófono.

**El principio general:**
> Limpiar de más es tan destructivo como no limpiar. En un sistema que mide
> errores, el ruido y la señal se parecen muchísimo.

Mencionar el timeout de 15 segundos: no es un ítem perdido, es un dato, y entra
al vector como `timeout_rate`.

---

## 5 · Detección de errores — 1:30

**Se dice:** las `editops` de Levenshtein alinean las dos cadenas y devuelven
tres operaciones; cada una se tipifica. Señalar la tira de alineamiento en
pantalla: `barco` → `darco`.

> `b` por `d` no es una sustitución cualquiera. Es un par espejo. El detector
> conoce cuatro: b/d, p/q, m/w, n/u, y los marca como rotación visual en vez de
> sustitución genérica.

**Cerrar preparando la siguiente:** cuatro de los diez códigos salen de aquí. Los
otros seis necesitan mirar más allá del carácter — y antes de eso hay que
resolver un problema más incómodo.

---

## 6 · Qué no es dislexia — 1:45

**La diapositiva conceptualmente más importante de la primera mitad.**

**Se dice:**
> Un escolar mexicano escribe `sena` por `cena`. Eso es seseo. Es cómo se habla
> en este país. No es un marcador fonológico de dislexia, y si lo contamos como
> error, le subimos el riesgo a medio salón.

Recorrer la tabla: seseo, yeísmo, b/v, h muda — no cuentan. `g/j` sí, porque es
un error fonológico real.

**El detalle que demuestra el cuidado:**
> Con una excepción: la `h` del dígrafo `ch` sí se pronuncia. Si un niño escribe
> `cico` por `chico`, eso cambia la palabra. Ahí la omisión vuelve a ser
> diagnóstica.

**Por qué importa:** aquí es donde el proyecto deja de ser un ejercicio de
distancia de edición y se convierte en trabajo de dominio.

---

## 7 · El falso positivo — 1:30

**Se dice:** la regla de la `h` muda estaba escrita y probada. Pero el
refinamiento fonético solo corría en la rama `replace`, y omitir una letra es un
`delete`. La regla nunca se ejecutaba.

**La consecuencia, dicha despacio:**
> La `h` muda inflaba `OMI_rate`, que es una feature que el modelo sí usa. O sea:
> el sistema le subía el riesgo a niños con ortografía perfectamente normal.

**La lección metodológica:**
> Ninguna métrica agregada habría mostrado esto. El f1 no baja: el modelo aprende
> tan campante con la feature contaminada. Solo aparece leyendo qué rama del
> código toca cada tipo de operación.

---

## 8 · Palabra, estructura y léxico — 1:15

**Se dice:** las tres tarjetas, con un ejemplo cada una. `INV` es un anagrama
exacto; `SEG`/`UNI` comparan la cadena unida contra el número de palabras; `LEX`
detecta que una pseudopalabra se convirtió en palabra real.

**Detenerse en LEX:**
> Es el mejor ejemplo de feature con teoría detrás. Si al niño le pones `blaco` y
> escribe `blanco`, no está descifrando: está adivinando por la forma global de
> la palabra. Eso distingue un subtipo de dislexia de otro. No es un error más.

---

## 9 · Fonética y estructura — 1:15

**Se dice:** Doble Metaphone codifica cómo suena una palabra.

**El punto clave:**
> La misma distancia de edición significa cosas opuestas según este número. Si
> suenan idéntico, el niño escribió lo que oyó: error de escritura. Si suenan
> distinto, el error es visual — o falló el reconocedor de voz.

Los n-gramas miden cuánta estructura sobrevive: una letra cambiada conserva casi
todo; una transposición no.

---

## 10 · Las 28 features — 1:30

**Se dice:** las cuatro familias. No leerlas todas — están en el respaldo.

**Lo que sí hay que explicar son las razones:**
> Fíjense que varias features no son conteos, son razones. `rot_sus_ratio`,
> `inv_omi_ratio`, la brecha pseudo menos real. Un niño con muchos errores de
> todo tipo no es lo mismo que uno cuyos errores son casi todos rotaciones. El
> conteo no distingue eso; la proporción sí.

**La restricción dura:**
> El vector debe ser idéntico al del cuaderno de entrenamiento. Si divergen, el
> modelo recibe features inconsistentes y se equivoca en silencio, con la misma
> confianza de siempre.

---

## 11 · El modelo — 1:15

**Se dice:** dos RandomForest, 300 árboles, `class_weight="balanced"`, split
estratificado 80/20.

**Justificar las métricas, no solo nombrarlas:**
> Usamos `f1_macro` y exactitud balanceada porque las clases clínicas están
> desbalanceadas por naturaleza: hay muchos más casos leves que severos. Con
> exactitud simple, un modelo que dijera «leve» a todos acertaría mucho y no
> serviría para nada.

**Diapositiva corta a propósito** — el modelo es la parte breve, y que se note.

---

## 12 · La diapositiva incómoda — 2:00

**El centro de gravedad del mazo. No apurarla.**

**Se dice:**
> Cuando inspeccionamos el modelo entrenado, encontramos que 12 de las 28
> features tienen importancia exactamente cero. No son poco importantes: son
> cero. Eso solo pasa si fueron constantes en el conjunto de entrenamiento.

> Entre ellas está `teacher_score_norm`. Es decir: el cuestionario PRODISLEX que
> llena el docente, que es trabajo real de una persona, hoy no influye en nada.

**El remate:**
> El modelo se entrenó con 1500 muestras sintéticas. Su f1 de 0.95 mide ajuste a
> datos sintéticos, no exactitud clínica. Son dos cosas distintas y conviene no
> confundirlas, sobre todo cuando el sujeto es un niño de siete años.

**Si preguntan «¿entonces no sirve?»:** sirve como tamizaje orientativo y como
andamiaje completo para el modelo real; lo que falta es el dato clínico, y la
tubería para incorporarlo ya está construida (diapositiva 15).

---

## 13 · El bug que envenenaba el futuro — 1:45

**Se dice:** `detect_word_level_errors` existía, estaba probado, y nunca se
llamaba. `INV`, `SEG` y `UNI` jamás se emitían.

**La parte contraintuitiva:**
> Lo interesante es que arreglarlo no cambia ni una predicción. Los árboles
> tienen importancia cero en esas columnas, nunca ramifican por ahí.
>
> Pero el vector que se persiste alimenta la tabla de entrenamiento. Sin
> corregirlo, el próximo modelo se entrenaría creyendo que ningún niño invierte
> letras — que es un marcador clásico de dislexia.

**La lección, que es la más transferible del mazo:**
> En un sistema que recolecta su propio dataset, un fallo de features no se mide
> en el modelo de hoy. Se paga en el de mañana.

---

## 14 · Señal dominante y contraste externo — 1:45

**Primera mitad:** el tiempo de respuesta pesa ~36 % entre tres features, y
medía mal: incluía el audio TTS y los ratos con la app en segundo plano.

> Corregirlo cambia diagnósticos ya emitidos. Muchos niños clasificados con
> perfil de fluidez dejan de estarlo. Por eso hay un script que cuantifica el
> corrimiento antes de desplegar: no se toca a ciegas la señal dominante de una
> herramienta que tamiza niños.

**Segunda mitad, el TEDE:** percentiles normados de 1974. No reemplazan al
modelo, lo acompañan. Si coinciden, el docente tiene respaldo; si difieren, hay
que revisar el modelo.

**La anécdota metodológica:**
> Al principio descartamos el subtest de Errores Específicos porque nuestros
> códigos de error no corresponden a sus 71 ítems. Y era cierto. Lo que no
> vimos es que correspondían los ítems mismos, que ya estaban cargados en el
> banco. El error estaba en el nivel de abstracción del mapeo, no en el
> instrumento.

---

## 15 · El bucle que falta cerrar — 1:30

**Se dice:** recorrer el diagrama. El especialista corrige un diagnóstico; se
guarda el vector con la etiqueta confirmada y sin datos personales; el script de
reentrenamiento consume esa tabla con un mínimo de 50 casos por clase; escribe en
`candidates/` y **nunca sobrescribe producción**; la promoción es una decisión
humana comparando métricas.

**El dato final:**
> Hoy esa tabla tiene cero etiquetas. La tubería está construida y esperando al
> primer especialista.

**Las tres ideas de cierre:**
> 1. El modelo es la última etapa, y la más corta.
> 2. Casi toda la señal se decide en qué errores no cuentan.
> 3. Un dataset sintético da métricas, no evidencia.

---

## Control de tiempo

| Bloque | Diapositivas | Acumulado |
|---|---|---|
| Apertura y dato | 1–3 | 2:30 |
| PLN: preprocesado y errores | 4–8 | 9:15 |
| Features y modelo | 9–11 | 13:15 |
| Validación y cierre | 12–15 | 20:15 |

**Si vas retrasado:** recorta la 9 (fonética) a una frase y la 11 (el modelo) a
treinta segundos. **No recortes la 6, la 12 ni la 13** — son el argumento.

**Si vas adelantado:** amplía la 6 con más ejemplos de seseo y yeísmo, o abre el
respaldo R1 con el catálogo completo de códigos.

---

## Preguntas preparadas

**Si el f1 mide datos sintéticos, ¿el sistema sirve para algo?**
Sirve como tamizaje orientativo —nunca como diagnóstico clínico, y así se declara
en la app— y sobre todo como andamiaje completo: el pipeline de PLN, las 28
features y el bucle de reetiquetado ya existen. Lo que falta es el dato clínico,
no la infraestructura.

**¿Por qué RandomForest y no una red neuronal?**
Con 1500 muestras y 28 features una red profunda no tiene con qué generalizar. Y
hay una razón mejor: el bosque da importancia por feature, que es justamente lo
que reveló el problema del dataset. Un modelo opaco con f1 0.95 habría ocultado
que doce features no hacían nada. *(Respaldo 2.)*

**¿Cómo distinguen un error del niño de un error del reconocedor de voz?**
Parcialmente, y es una limitación real. La similitud fonética ayuda: si suenan
idéntico es más probable que sea escritura; si suenan distinto puede ser
cualquiera de los dos. Por eso la corrección de artefactos STT solo se aplica
cuando la respuesta vino de micrófono. *(Respaldo 3.)*

**¿No es arriesgado descartar errores por dialecto?**
El riesgo contrario es mayor. Contar el seseo como marcador de dislexia le sube
el riesgo a una porción enorme de niños que hablan normalmente. Las reglas están
acotadas a fenómenos documentados del español mexicano y se registran igual en el
desglose: se marcan como no diagnósticas, no se borran.

**¿Cuántas muestras necesitan para reentrenar de verdad?**
El script exige 50 por clase como mínimo, que es el umbral que fija la propia
tabla. No es un número mágico: es el piso por debajo del cual un modelo clínico
ajustado a un puñado de casos sería peor que el actual, aunque sus métricas se
vean mejor.

**¿Por qué un baremo de 1974?**
Porque es el que existe estandarizado para población hispanohablante en este
subtest, y sirve como contraste independiente del modelo. No se presenta como
verdad: se presenta al lado de la predicción, y que difieran también es
información.
