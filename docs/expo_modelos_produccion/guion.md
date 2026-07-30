# Guion del expositor — Modelos en producción

**Duración objetivo:** 15–20 min · 15 diapositivas + 3 de respaldo
**Mazo:** `docs/expo_modelos_produccion/index.html` (flechas ← → o barra espaciadora)

> **Regla de honestidad del mazo:** todo lo que se afirma existe en el repositorio.
> Las diapositivas 13 y 14 van marcadas como propuesta y hay que decirlo en voz
> alta, no solo mostrarlo. Si el jurado sale creyendo que el asistente ya funciona,
> la exposición falló aunque haya gustado.

---

## 1 · Portada — 0:30

**Se dice:**
> Este proyecto detecta riesgo de dislexia en primaria. Tiene dos modelos de
> machine learning entrenados y funcionando. Y de los tres meses de trabajo, el
> entrenamiento fue lo más rápido. Hoy quiero hablar de todo lo demás: cómo se
> sirve un modelo, cómo se despliega, cómo se integra, y qué pasa cuando se cae.

**No se dice:** nada del RAG todavía. Aparece anunciado en la portada ya marcado
como propuesta; si alguien pregunta, «llegamos a eso al final».

---

## 2 · Qué es CogniFit — 1:00

**Se dice:** primaria de 1º a 5º, 6 a 10 años, foco en zonas de alta marginación.
Las seis fases de un vistazo. Y la frase que importa:

> No emitimos un diagnóstico clínico. Detectamos indicadores tempranos y
> orientamos al docente para derivar. Eso no es un descargo legal: es lo que
> define qué le podemos pedir al modelo y qué no.

**Por qué está aquí:** fija el marco ético antes de hablar de tecnología. Si el
jurado va a cuestionar algo, mejor que sea después de haberlo dicho tú.

---

## 3 · Arquitectura — 1:30

**Se dice:** cinco servicios. Flutter, el gateway, los dos servicios de PLN,
Postgres y Redis. Señalar que **solo el gateway se expone**.

> Los puertos 8001 y 8002 no existen para el mundo exterior. La app no sabe que
> hay microservicios detrás, y eso es deliberado: podemos mover, reemplazar o
> tirar un servicio sin tocar el cliente.

**No se dice:** el detalle de cada servicio. Vienen en los bloques siguientes.

---

## 4 · Inferencia I — el vector de 28 dimensiones — 1:30

**Se dice:** el alumno dicta o escribe; lo que llega es texto sucio con timeouts.
Cuatro pasos hasta el vector. Los nombres de las features son el vocabulario
clínico del error disléxico convertido en tasas: omisión, sustitución, inversión,
rotación.

**El momento fuerte** — leer el comentario del archivo tal cual:

> «DEBE producir vectores idénticos a los del notebook de entrenamiento, de lo
> contrario el modelo recibirá features inconsistentes.»
>
> Ese comentario es el problema número uno de los modelos en producción y tiene
> nombre: *training-serving skew*. El modelo no se rompe con un error: sigue
> respondiendo, con la misma confianza, y se equivoca en silencio.

**No se dice:** las 28 features una por una. Se muestran 14 y se sigue.

---

## 5 · Inferencia II — dos clasificadores — 1:30

**Se dice:** subtipo y severidad son preguntas distintas, con un modelo cada una.
Ambos devuelven `predict_proba`, así que el sistema sabe cuándo no está seguro.
Se cargan una vez en el `lifespan` de FastAPI, no por petición.

Sobre la elección de scikit-learn: dataset pequeño, features interpretables, y el
resultado tiene que poder explicársele a un docente.

**No se dice:** métricas concretas del modelo. Si preguntan, están en
`/model/info` y hay respaldo preparado (ver §Preguntas).

---

## 6 · Inferencia III — el contrato — 1:30

**Se dice:** tres endpoints y qué hace cada uno. Rematar con el versionado:

> El versionado no es un campo en una tabla, es una restricción. La base rechaza
> promover un modelo a producción si no trae métricas validadas. No depende de que
> alguien se acuerde de revisarlo.

Y por qué `dataset_sha256` importa: sin él no se puede saber con qué datos se
entrenó el modelo que produjo un diagnóstico concreto.

---

## 7 · Despliegue I — el orden de arranque — 1:30

**Se dice:** `depends_on: service_healthy`. El gateway no acepta tráfico hasta que
los modelos están en memoria.

> Sin esa condición, el servicio arranca «sano» y las primeras peticiones después
> de cada despliegue fallan. Es el tipo de error que solo aparece en producción y
> solo durante veinte segundos.

Mencionar el pin de `scikit-learn` en 1.8.0 para que coincida con la versión que
serializó los `.pkl`. Es un detalle pequeño que ilustra bien el punto: el modelo
no es solo el archivo, es el archivo *más su entorno*.

---

## 8 · Despliegue II — el incidente — 2:00

**La diapositiva más importante del mazo. No apurarla.**

**Se dice, en este orden:**

1. `/health/pln` devolvía los dos servicios caídos, con el campo `error` vacío.
2. Nuestra primera hipótesis: IPv4 contra la red privada IPv6 de Railway. El
   razonamiento era coherente — un `error` vacío es un `ConnectTimeout`, luego el
   proceso está vivo pero inalcanzable.
3. **Era falsa.** Un contenedor en bucle de reinicio da el mismo síntoma: los
   paquetes hacia un contenedor muerto se descartan en vez de rechazarse. El
   tiempo agotado no distinguía entre «escucha en la interfaz equivocada» y «no
   escucha en absoluto».
4. La causa real estaba en la primera línea de los logs: un comando de inicio
   personalizado pasaba `--port $PORT` sin shell, y uvicorn recibía la cadena
   literal.

**El remate** — leerlo del documento:

> «Lo que faltó fue mirar los logs del servicio antes de teorizar.»

**Por qué contar un fallo propio:** un jurado ha visto muchas exposiciones donde
todo salió bien. Contar un diagnóstico equivocado, y por qué era razonable pero
incorrecto, demuestra criterio mejor que cualquier diagrama.

---

## 9 · Despliegue III — degradación elegante — 1:30

**Se dice:**
> Esta es, para mí, la pregunta que separa un modelo entrenado de un modelo en
> producción: ¿qué pasa cuando el modelo no está?

Las dos mitades: `PLN_FALLBACK_ENABLED` hace que el pipeline local responda igual,
y `pln_source='local_fallback'` deja el rastro en la base para repetir después
esos diagnósticos.

**El remate:**
> Degradar sin avisar es esconder el problema. Degradar dejando rastro es una
> decisión de diseño.

---

## 10 · Integración I — el gateway — 1:30

**Se dice:** las cuatro responsabilidades del gateway. Rematar con:

> El modelo no se expone a internet. Se expone un caso de uso —«diagnostica esta
> sesión»— y el modelo es un detalle de implementación detrás de él.

---

## 11 · Integración II — los clientes — 1:00

**Se dice:** el `AsyncClient` reutilizable y por qué. El reintento ante 503, que es
justo lo que devuelve el servicio mientras carga los modelos: el cliente conoce el
ciclo de vida del servicio con el que habla.

Cerrar señalando las tres variables de entorno: definen qué hace el sistema
cuando el modelo tarda, falla o desaparece.

**Diapositiva corta a propósito** — sirve de respiro entre dos bloques densos.

---

## 12 · Integración III — Flutter — 1:30

**Se dice:** lo interesante no es la pantalla, es qué hace cuando falla la red.
Cola offline en sqflite, refresh de token en 401, TTS y STT en español de México,
`FLAG_SECURE` para que no se puedan capturar pantallas con datos de menores.

**El remate:**
> Un modelo servido por una API que la app no puede alcanzar la mitad del tiempo
> no es un modelo en producción. Es un modelo con una URL.

**Contexto que ayuda:** las escuelas donde esto se usa no tienen buena conexión.
El modo offline no es una función extra, es un requisito del entorno.

---

## 13 · RAG, propuesta I — el hueco — 1:30

**Abrir diciéndolo, no solo mostrándolo:**
> Lo que viene ahora no está implementado. Es la propuesta con la que cerramos.

**Se dice:** el clasificador dice qué tiene el alumno; el recomendador entrega
ejercicios de bancos etiquetados a mano. Falta quien responda «¿y ahora qué hago
con este niño?». Y el material bueno está en PDF, fuera del alcance del sistema.

**El dato que se recuerda** — señalar la gráfica:
> Sexto grado tiene cero ejercicios. Un alumno de 6º con dislexia severa recibe
> hoy material etiquetado para 1º y 2º. El servicio ya lo detecta y lo marca como
> `grade_appropriate: false`. Pero señalar un problema no es resolverlo.

---

## 14 · RAG, propuesta II — cómo se construiría — 1:30

**Se dice:** los cuatro pasos, rápido. Detenerse en dos puntos:

- Los embeddings corren en local: **el material no sale del sistema para
  vectorizarse**.
- pgvector va sobre el PostgreSQL que ya está desplegado: no hace falta
  infraestructura nueva.

**La advertencia, que conviene decir tú antes de que la digan ellos:**
> Un asistente sobre material clínico puede sonar perfectamente convincente y
> estar equivocado. Por eso la citación obligatoria no es un adorno: es lo que lo
> vuelve utilizable por un docente, porque puede ir a verificar la fuente.

Cerrar con la columna de lo que falta, sin dramatizar: sin CI, sin observabilidad,
sin detección de deriva. **Saber qué falta, y por qué, también es parte del
sistema.**

---

## 15 · Cierre — resto del tiempo

Las tres ideas, una frase cada una. No leerlas de la pantalla.

> 1. El modelo es la pieza pequeña.
> 2. Producción es decidir qué pasa cuando el modelo no está.
> 3. Saber qué no tienes es parte del sistema.

Y cerrar: «Gracias. Preguntas.»

---

## Control de tiempo

| Bloque | Diapositivas | Acumulado |
|---|---|---|
| Apertura y contexto | 1–3 | 3:00 |
| Inferencia | 4–6 | 7:30 |
| Despliegue | 7–9 | 12:30 |
| Integración | 10–12 | 16:30 |
| Propuesta y cierre | 13–15 | 19:30 |

**Si vas retrasado:** recorta la 11 (la más corta y prescindible) y resume la 12
en una frase. No recortes la 8 ni la 9 — son el corazón del argumento.

**Si vas adelantado:** amplía la 8 con el detalle de por qué `sh -c` expande la
variable y la forma exec no.

---

## Preguntas preparadas

**¿Por qué scikit-learn y no una red neuronal?**
El dataset es pequeño; una red profunda no tenía con qué generalizar. Las 28
features salen de teoría existente sobre el error disléxico, no de una capa
oculta, así que son interpretables una por una. Y un docente puede preguntar por
qué salió ese resultado. *(Respaldo 3.)*

**¿Cómo saben que el modelo sigue siendo válido?**
Respuesta honesta: hay versionado con métricas y una restricción en la base que
impide promover un modelo sin validar. **No hay detección de deriva.** Hoy nadie
mide si el modelo se degrada con datos reales, y es de lo primero que haría falta.

**¿Esto está en producción de verdad?**
Está desplegado en Railway, y ahí tuvimos el incidente de la diapositiva 8. El
sistema tiene fallback local, así que sigue produciendo diagnósticos aunque los
servicios ML estén caídos, y lo registra como tal. *(Si preguntan si hoy corre
con los modelos o con el fallback: verificarlo antes de la exposición con
`GET /api/v1/health/pln` y responder con el dato real.)*

**¿Qué pasa con los datos de menores?**
Cifrado de campos sensibles, RLS por institución, consentimiento del tutor,
auditoría de escritura y bloqueo de capturas de pantalla en la app. Sobre el RAG
propuesto: consultaría material didáctico, no expedientes; no se enviarían datos
de alumnos.

**¿Por qué no implementaron el RAG?**
Porque preferimos exponer lo que funciona y decir con claridad qué no existe. El
diseño está hecho —está en el repositorio como especificación— y la decisión fue
no presentar como terminado algo que no lo está.

**¿Cuánto costaría operarlo?**
Vectorización y almacenamiento, cero: los embeddings corren en el propio servidor
y pgvector va sobre la base que ya existe. El único costo variable es la
generación, por consulta. *(Respaldo 2.)*

**¿Por qué el banco de ejercicios está incompleto?**
Porque cargar contenido pedagógico sin que lo revise un especialista sería peor
que no tenerlo. Hay una propuesta de trece ejercicios para 4º a 6º escrita y
esperando revisión.
