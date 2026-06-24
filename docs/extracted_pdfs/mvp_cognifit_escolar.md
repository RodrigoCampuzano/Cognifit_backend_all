# MVP — CogniFit Escolar.pdf

- Archivo original: `C:\Users\camcl\Downloads\MVP — CogniFit Escolar.pdf`
- Paginas: 5

## Metadatos

- `/Title`: MVP — CogniFit Escolar
- `/Producer`: Skia/PDF m151 Google Docs Renderer

## Contenido por pagina

### Pagina 1

MVP — CogniFit Escolar
Proyecto
Descripción del proyecto
CogniFit Escolar es una plataforma inteligente para la detección temprana, intervención
adaptativa y seguimiento continuo de la dislexia en alumnos de educación primaria en
México. El sistema automatiza el análisis de patrones de escritura y lectura mediante
Procesamiento de Lenguaje Natural (PLN) y Machine Learning, permitiendo al docente
obtener un diagnóstico probabilístico del alumno, asignarle ejercicios terapéuticos ajustados
a su perfil y monitorear su evolución en el tiempo, todo desde una aplicación móvil, sin
necesitar la presencia de un especialista en el aula.
El problema que resuelve es crítico: en México el 7% de la población presenta dislexia
(UNAM), la mayoría sin diagnóstico oportuno. En estados con alta marginación como
Chiapas, la escasez de psicopedagogos en escuelas públicas deja a los docentes sin
herramientas objetivas para identificar la condición a tiempo. CogniFit cierra esa brecha
entregando al docente un asistente terapéutico basado en evidencia, accesible desde su
dispositivo móvil.
Funcionalidades
Docente
● Registro e inicio de sesión con autenticación segura (JWT + Argon2).
● Gestión de alumnos por grupo y grado.
● Asignación del test de diagnóstico inicial.
● Consulta del perfil clínico del alumno: subtipo de dislexia, nivel de severidad y
historial de evaluaciones.
● Visualización de curva de aprendizaje (gráficas de evolución de errores).
● Recepción de alertas automáticas de estancamiento.
● Generación y descarga de reportes PDF para padres y especialistas.
● Vista resumen del grupo con alumnos ordenados por nivel de riesgo.
Alumno
● Interfaz multisensorial accesible, adaptada para perfiles disléxicos.
● Tests diagnósticos: pruebas léxico-visuales, pseudopalabras y dictado (STT).
● Ejercicios de intervención dinámica ajustados en tiempo real según desempeño.
● Retroalimentación visual y auditiva inmediata ante errores específicos de dislexia.
● Persistencia local: reanuda ejercicios si se pierde la conexión.
Administrador

### Pagina 2

● Gestión de cuentas de todos los roles.
● Monitoreo del estado de los microservicios.
● Gestión de versiones del modelo de ML y consulta de métricas de rendimiento.
● Consulta de logs del sistema.
Puntos Críticos a Presentar
1. Flutter → Móvil
La aplicación móvil se desarrolla en Flutter (Dart) con arquitectura limpia y slicing vertical.
Flutter fue elegido por su capacidad multiplataforma (Android/iOS desde un solo código
base), su soporte nativo a TTS/STT para los ejercicios multisensoriales, y su alto
rendimiento en animaciones de retroalimentación visual en tiempo real.
Puntos técnicos clave:
● Riverpod para gestión de estado reactiva y desacoplada de la UI.
● go_router para navegación declarativa con guards de autenticación.
● Dio como cliente HTTP con interceptor JWT centralizado.
● FLAG_SECURE activo en pantallas con datos clínicos de menores (bloquea
capturas de pantalla).
● TTS/STT integrados para dictado y lectura en voz alta en ejercicios multisensoriales.
● Persistencia local del estado del ejercicio para soporte sin conexión.
2. Minería de Datos
El núcleo inteligente del sistema se compone de dos etapas principales:
Diagnóstico (PLN + ML):
● spaCy (es_core_news_md) procesa el texto producido por el alumno: tokenización,
lematización y NER adaptado para detectar errores de dislexia (inversiones,
rotaciones, omisiones y sustituciones fonológicas).
● Adaptaciones de Metaphone/Soundex al español y extracción de n-gramas de
caracteres identifican similitudes estructurales y errores fonéticos.
● TF-IDF Vectorizer convierte los patrones detectados en la matriz de características
numérica.
● Un clasificador Random Forest / SVM (validados con métricas cruzadas) emite el
subtipo (fonológica, superficial/visual, mixta), la severidad (leve, moderado, severo) y
la probabilidad de riesgo.
Seguimiento y recalibración (Series Temporales + Recomendación):
● El módulo de seguimiento analiza el historial de sesiones como serie temporal:
rastrea la curva de errores por minuto, tiempo de respuesta y aciertos por ejercicio.

### Pagina 3

● Si el alumno supera el 90% de aciertos en los últimos N ejercicios, el sistema
recalibra automáticamente al nivel superior sin necesidad de un test nuevo.
● Si no hay mejora en N sesiones, genera una alerta de estancamiento para el
docente.
● El motor de recomendación adaptativa mapea diagnóstico → ruta de aprendizaje:
un perfil fonológico leve recibe ejercicios de conciencia fonológica básica; un perfil
mixto severo recibe apoyo visual, auditivo y segmentación silábica cromática.
Dataset: texto en español con inyección de ruido disléxico sintético (inversiones,
omisiones, sustituciones) adaptado al español mexicano, documentado con pandas/NumPy
y trazabilidad de versiones.
3. SOA (Arquitectura Orientada a Servicios)
CogniFit implementa una arquitectura SOA con microservicios independientes, cada
uno con responsabilidad única y despliegue en contenedor Docker:
Microservicio Responsabilidad
Auth Service Registro, login, emisión y validación de JWT
User & Groups Service Gestión de cuentas, escuelas, grupos,
alumnos
Test Service Aplicación de tests, captura de respuestas
Diagnosis Service Pipeline PLN + ML, clasificación de dislexia
Recommendation Service Motor de rutas de aprendizaje adaptativas
Exercise Service Entrega y registro de ejercicios dinámicos
Tracking & Alerts Service Series temporales, recalibración, alertas
Report Service Generación de PDFs con ReportLab
API Gateway como punto de entrada único: valida el JWT, enruta a los microservicios
internos, aplica rate limiting y oculta la topología del sistema. Base de datos PostgreSQL
compartida con esquemas separados por dominio; Redis para caché de respuestas
frecuentes.
4. Seguridad
Las medidas de seguridad del sistema responden al marco OWASP MASVS para la app
móvil y buenas prácticas de backend:

### Pagina 4

Capa Control aplicado
Autenticación JWT con expiración, hash Argon2 para contraseñas
Transporte HTTPS / TLS en toda la comunicación cliente-servidor
App móvil FLAG_SECURE bloquea capturas de pantalla en pantallas
clínicas
Datos en Cifrado de campos sensibles (diagnósticos de menores)
reposo
Acceso RBAC estricto: cada rol solo accede a sus recursos
Auditoría Log inmutable de acciones críticas con usuario y timestamp
Consentimiento Registro de consentimiento del tutor al crear cuenta de alumno
Modelo ML No se promueve a producción un modelo sin métricas validadas
La justificación de estas decisiones de seguridad fue evaluada mediante OCTAVE
ALLEGRO, identificando cuatro activos críticos (datos de diagnóstico de menores, modelo
ML, historial de sesiones y motor de recomendación) con sus vectores de amenaza y
estrategias de mitigación priorizadas.
Monetizar
Categoría o Temática
CogniFit Escolar pertenece a la categoría EdTech / HealthTech social: tecnología
educativa aplicada a necesidades de salud cognitiva, con impacto directo en el sistema
educativo público mexicano. Su temática central es la inclusión educativa mediante
inteligencia artificial accesible para contextos con escasez de especialistas.
Público Objetivo
Segmento Descripción
Primario Docentes de educación primaria pública en México, especialmente en
estados de alta marginación (Chiapas, Oaxaca, Guerrero)
Secundario Escuelas primarias públicas y privadas, zonas escolares y supervisiones
Terciario Padres/tutores de alumnos con sospecha de dislexia
Institucional Secretarías de Educación estatales, organizaciones civiles de inclusión
educativa, ONG enfocadas en rezago escolar

### Pagina 5

Modelo de monetización propuesto:
● Licencia por escuela/zona escolar (B2G/B2B): suscripción anual por institución
con número ilimitado de docentes y alumnos.
● Freemium con límite de alumnos: versión gratuita hasta N alumnos; plan premium
sin límite + reportes PDF ilimitados + dashboard de coordinador.
● Integración institucional con SEP / INEE: licenciamiento a nivel estatal como
herramienta de política pública de inclusión.
● Módulo de capacitación docente: venta de cursos cortos certificados sobre
detección e intervención de dislexia con la plataforma.
