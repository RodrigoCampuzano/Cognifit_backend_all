# ADR — CogniFit Escolar
**Equipo:** Carlos Daniel Solis Aguilar · Rodrigo Emilio Campuzano Culebro · Alicia Montserrat Valenti Ruiz  
**Universidad Politécnica de Chiapas — Ingeniería en Software**  
**Proyecto Integrador — Registro de Decisiones Arquitectónicas**

---

## Carlos — Minería de Datos / Microservicios ML (ADR-01 a ADR-14)

---

### ADR-01 · Pipeline de Análisis Fonético
**Requerimiento:** HU-MD-01 — Pipeline PLN a nivel de caracteres y fonético  
**Patrón:** Chain of Responsibility (GoF)

**Contexto:** El sistema necesita detectar inversiones, omisiones, rotaciones y sustituciones fonológicas en texto de alumnos mediante múltiples etapas secuenciales de procesamiento que deben ejecutarse en orden y ser extensibles sin modificar las anteriores.

**Decisión:** Implementar la canalización de análisis como Chain of Responsibility, donde cada etapa procesa el texto y delega al siguiente eslabón de la cadena.

**Consecuencias:**
- Permite agregar nuevos filtros fonéticos sin modificar etapas existentes.
- Facilita pruebas unitarias aisladas por cada eslabón de la cadena.
- Introduce ligera sobrecarga por el encadenamiento secuencial de llamadas.

---

### ADR-02 · Adaptador de Vectorización TF-IDF
**Requerimiento:** HU-MD-02 — Extracción de características (TF-IDF)  
**Patrón:** Adapter (GoF)

**Contexto:** El módulo de extracción de características depende de scikit-learn, librería externa cuya interfaz puede cambiar entre versiones, y el pipeline propio de PLN necesita desacoplarse de esa dependencia concreta para garantizar estabilidad.

**Decisión:** Aplicar un Adapter que envuelva TfidfVectorizer de scikit-learn detrás de una interfaz propia de extracción de características reutilizable.

**Consecuencias:**
- Aísla al pipeline de cambios futuros en la librería externa.
- Permite sustituir TF-IDF por otro vectorizador sin romper contratos.
- Agrega una capa adicional que debe mantenerse sincronizada con la librería.

---

### ADR-03 · Selección Intercambiable de Clasificador
**Requerimiento:** HU-MD-03 — Clasificador de subtipo y severidad  
**Patrón:** Strategy (GoF)

**Contexto:** El equipo necesita comparar Random Forest y SVM como candidatos para clasificar subtipo y severidad de dislexia, y el modelo seleccionado en producción puede cambiar conforme se reentrena con nuevas versiones del dataset.

**Decisión:** Usar el patrón Strategy para encapsular Random Forest y SVM como algoritmos intercambiables tras una interfaz común de clasificación.

**Consecuencias:**
- Permite cambiar de algoritmo activo sin modificar el servicio de diagnóstico.
- Facilita añadir futuros clasificadores como nuevas estrategias.
- Requiere mantener una interfaz de predicción consistente entre modelos.

---

### ADR-04 · Validación Cruzada con Plantilla
**Requerimiento:** HU-MD-04 — Validación y métricas del modelo  
**Patrón:** Template Method (GoF)

**Contexto:** Evaluar cualquier candidato de clasificador requiere siempre los mismos pasos secuenciales: particionar el dataset, entrenar, calcular accuracy y F1, y registrar métricas por versión, independientemente del algoritmo bajo prueba.

**Decisión:** Definir un Template Method que fije el esqueleto del pipeline de validación cruzada y delegue únicamente el paso de entrenamiento al algoritmo concreto.

**Consecuencias:**
- Garantiza que todos los modelos se evalúen bajo exactamente el mismo proceso.
- Evita duplicar los pasos de partición y registro de métricas por cada algoritmo.
- Limita flexibilidad si un futuro modelo requiere pasos de evaluación muy distintos.

---

### ADR-05 · Construcción de Dataset Sintético
**Requerimiento:** HU-MD-05 — Dataset y ruido disléxico sintético  
**Patrón:** Builder (GoF)

**Contexto:** Generar el dataset de entrenamiento implica pasos opcionales y configurables como cargar texto base, inyectar ruido disléxico, etiquetar errores y versionar, y se necesita ensamblar el resultado de forma controlada y reproducible.

**Decisión:** Emplear un Builder que construya el dataset paso a paso, permitiendo combinar transformaciones de ruido de forma reproducible y trazable.

**Consecuencias:**
- Facilita generar variantes del dataset cambiando solo los pasos del builder.
- Mejora la trazabilidad y reproducibilidad de cada versión generada.
- Añade complejidad inicial frente a una generación de dataset directa.

---

### ADR-06 · Estrategias de Recomendación Adaptativa
**Requerimiento:** HU-MD-06 — Motor de recomendación adaptativa  
**Patrón:** Strategy (GoF)

**Contexto:** El motor de recomendación debe asignar rutas de aprendizaje distintas según el subtipo y severidad de dislexia detectados, y las reglas de asignación pueden evolucionar conforme se valida su efectividad clínica con datos reales.

**Decisión:** Implementar Strategy para encapsular las reglas de mapeo diagnóstico-ejercicios, permitiendo intercambiar la lógica de recomendación por subtipo de forma independiente.

**Consecuencias:**
- Permite ajustar reglas clínicas sin tocar el resto del servicio.
- Facilita pruebas A/B entre distintas estrategias de recomendación.
- Exige definir una interfaz común para todas las estrategias de mapeo.

---

### ADR-07 · Notificación de Tendencias Temporales
**Requerimiento:** HU-MD-07 — Análisis de series temporales  
**Patrón:** Observer (GoF)

**Contexto:** El analizador de series temporales detecta mejoras, estancamientos o retrocesos en el desempeño del alumno, y componentes como alertas y recalibración necesitan reaccionar a esos cambios sin acoplarse directamente al analizador.

**Decisión:** Aplicar Observer para que el analizador de tendencias notifique a los suscriptores interesados en cada cambio de tendencia detectado.

**Consecuencias:**
- Desacopla el análisis temporal de los módulos que reaccionan a él.
- Permite agregar nuevos observadores sin modificar el analizador base.
- Puede dificultar rastrear el orden de notificaciones en producción.

---

### ADR-08 · Estados de Nivel del Alumno
**Requerimiento:** HU-MD-08 — Recalibración automática de dificultad  
**Patrón:** State (GoF)

**Contexto:** La dificultad de los ejercicios de cada alumno debe transicionar entre niveles leve, moderado y severo según su desempeño reciente, y cada nivel habilita un comportamiento distinto en la selección de ejercicios del sistema.

**Decisión:** Modelar el nivel del alumno con el patrón State, encapsulando las reglas de transición y el comportamiento de selección por cada nivel.

**Consecuencias:**
- Evita condicionales extensos para decidir el comportamiento según nivel.
- Facilita agregar nuevos niveles o reglas de transición en el futuro.
- Incrementa el número de clases necesarias para representar los estados.

---

### ADR-09 · Eventos de Estancamiento del Alumno
**Requerimiento:** HU-MD-09 — Generación de alertas de estancamiento  
**Patrón:** Domain Event (Fowler)

**Contexto:** Cuando el sistema detecta que un alumno no progresa tras varias sesiones consecutivas, debe generar una alerta para el docente sin que el módulo de seguimiento dependa directamente de la lógica de notificaciones del sistema.

**Decisión:** Emitir un Domain Event de estancamiento que otros servicios escuchan para crear y enviar la alerta correspondiente al docente.

**Consecuencias:**
- Desacopla la detección del estancamiento de la entrega de la alerta.
- Permite que múltiples consumidores reaccionen al mismo evento emitido.
- Requiere infraestructura de mensajería o mecanismo de despacho de eventos.

---

### ADR-10 · DTO para Métricas de Evolución
**Requerimiento:** HU-MD-10 — Visualización de métricas de evolución  
**Patrón:** Data Transfer Object (Fowler)

**Contexto:** El panel del docente necesita series de errores y tiempos de respuesta listas para graficar, mientras que internamente las métricas se calculan con estructuras propias del módulo de minería de datos en Python.

**Decisión:** Definir un Data Transfer Object que empaquete las métricas calculadas en un formato simple y listo para el consumo del frontend.

**Consecuencias:**
- Evita exponer estructuras internas del módulo de minería de datos.
- Simplifica el consumo de métricas desde React con Recharts.
- Añade un paso de mapeo entre el modelo interno y el DTO exportado.

---

### ADR-11 · Gateway de Versiones del Modelo
**Requerimiento:** HU-MD-11 — Métricas de rendimiento del modelo  
**Patrón:** Gateway (Fowler)

**Contexto:** El administrador necesita consultar y cambiar la versión activa del modelo de ML, y el acceso al almacenamiento de versiones y métricas debe centralizarse para evitar consultas dispersas por distintos módulos del sistema.

**Decisión:** Centralizar el acceso al almacenamiento de versiones mediante un Gateway que expone operaciones simples de consulta y cambio de versión activa.

**Consecuencias:**
- Aísla al resto del sistema de los detalles de almacenamiento de versiones.
- Facilita cambiar el mecanismo de persistencia sin afectar consumidores.
- Introduce un punto único que debe mantenerse disponible para el administrador.

---

### ADR-12 · Fachada del Servicio de Diagnóstico
**Requerimiento:** HU-BK-06 — Microservicio de diagnóstico  
**Patrón:** Facade (GoF)

**Contexto:** El Diagnosis Service combina internamente varios subsistemas como PLN, extracción de características y clasificador, pero los clientes externos como el Test Service solo necesitan enviar texto y recibir un diagnóstico estructurado.

**Decisión:** Exponer una Facade que unifique PLN, extracción de características y clasificación tras un único endpoint de diagnóstico para clientes externos.

**Consecuencias:**
- Simplifica la integración del Test Service con el pipeline interno.
- Oculta la complejidad y los cambios internos del módulo de ML.
- Puede convertirse en cuello de botella si el pipeline interno crece demasiado.

---

### ADR-13 · Mediador del Servicio de Recomendación
**Requerimiento:** HU-BK-07 — Microservicio motor de recomendación  
**Patrón:** Mediator (GoF)

**Contexto:** El Recommendation Service debe coordinar información del diagnóstico, el banco de ejercicios y la ruta previa del alumno sin que estos componentes se conozcan ni dependan directamente entre sí dentro del microservicio.

**Decisión:** Introducir un Mediator que coordine diagnóstico, banco de ejercicios y ruta previa para generar la nueva ruta de aprendizaje.

**Consecuencias:**
- Reduce el acoplamiento directo entre los componentes del servicio.
- Centraliza la lógica de coordinación en un único lugar controlable.
- El mediador puede volverse complejo si crecen las reglas de negocio.

---

### ADR-14 · Capa de Servicio de Ejercicios
**Requerimiento:** HU-BK-08 — Microservicio de ejercicios dinámicos  
**Patrón:** Service Layer (Fowler)

**Contexto:** La app Flutter necesita un punto de entrada claro para pedir el siguiente ejercicio, enviar resultados y disparar la recalibración, sin acoplarse a la lógica interna de selección y ajuste dinámico de dificultad del microservicio.

**Decisión:** Definir un Service Layer que exponga las operaciones de ejercicios disponibles para la app sin exponer la lógica interna del microservicio.

**Consecuencias:**
- Define un contrato claro y estable para el cliente Flutter.
- Permite reorganizar la lógica interna sin romper la API pública.
- Agrega una capa adicional entre el endpoint HTTP y la lógica de dominio.

---

## Rodrigo — Backend SOA / Base de Datos (ADR-15 a ADR-27)

---

### ADR-15 · Proxy de Autenticación JWT
**Requerimiento:** HU-BK-01 — Autenticación y registro seguro  
**Patrón:** Proxy (GoF)

**Contexto:** Las rutas protegidas del backend necesitan validar el token JWT antes de permitir acceso a datos clínicos sensibles, sin que cada microservicio reimplemente la lógica de verificación de forma independiente y dispersa.

**Decisión:** Implementar un Proxy de protección que intercepte las peticiones y valide el JWT antes de delegar al recurso real solicitado.

**Consecuencias:**
- Centraliza la verificación de autenticación en un solo componente.
- Evita duplicar lógica de validación en cada microservicio del sistema.
- Añade una capa de indirección en cada petición que requiere protección.

**Estado de implementación:** cumplido. `require_roles()` en `api/dependencies/auth.py`
intercepta la petición, valida el JWT vía `get_current_user` y delega solo si el rol
autorizado coincide — usado como `Depends()` en todos los endpoints protegidos.

---

### ADR-16 · Gateway de Enrutamiento Único
**Requerimiento:** HU-BK-02 — API Gateway como punto de entrada único  
**Patrón:** Gateway (Fowler)

**Contexto:** Los clientes como la app móvil y el panel web necesitan un único punto de acceso que oculte la topología interna de ocho microservicios y centralice autenticación y rate limiting sin exponer las direcciones internas.

**Decisión:** Implementar un Gateway que enrute, autentique y aplique límites de tasa antes de delegar a los microservicios internos correspondientes.

**Consecuencias:**
- Oculta la complejidad interna de la arquitectura SOA al cliente externo.
- Centraliza políticas de seguridad y limitación de tráfico en un punto.
- Se convierte en punto crítico de fallo que requiere alta disponibilidad.

**Estado de implementación:** cumplido como Gateway lógico, no como servicio separado.
El MVP no levanta ocho microservicios independientes (el Diagnosis/Recommendation Service
son clientes HTTP opcionales con fallback local — ver ADR-12), así que no hay topología
real que enrutar. El stack de middlewares en `api/main.py` (`SecurityHeadersMiddleware` →
`RateLimitMiddleware` → `AuthContextMiddleware` → `RequestLoggingMiddleware`) cumple el rol
del Gateway: único punto de entrada que centraliza auth, rate limiting y logging antes de
que cualquier request llegue a un router. Se documenta así deliberadamente en vez de
construir infraestructura de enrutamiento sin microservicios reales detrás.

---

### ADR-17 · Repositorio de Cuentas de Usuario
**Requerimiento:** HU-BK-03 — Gestión de cuentas (Administrador)  
**Patrón:** Repository (Fowler)

**Contexto:** El administrador necesita operaciones CRUD sobre cuentas de los cuatro roles sin acoplar la lógica de negocio a detalles de PostgreSQL, manteniendo borrado lógico y unicidad de correo como reglas centralizadas.

**Decisión:** Encapsular el acceso a usuarios mediante un Repository que exponga operaciones de colección y centralice las reglas de unicidad y rol.

**Consecuencias:**
- Aísla la lógica de negocio del motor de persistencia concreto.
- Facilita aplicar reglas de unicidad y borrado lógico en un punto.
- Agrega una capa intermedia sobre operaciones de base de datos simples.

**Estado de implementación:** cumplido. `UserRepository` en
`infrastructure/security/user_repository.py` centraliza `create_user`, `get_by_email`,
`update_user`, `deactivate_user` — usado por `api/v1/admin/router.py`.

---

### ADR-18 · Consulta Filtrada de Alumnos
**Requerimiento:** HU-BK-04 — Gestión de alumnos por grupo y grado  
**Patrón:** Query Object (Fowler)

**Contexto:** El docente solo debe ver alumnos de sus propios grupos, y las consultas paginadas por grado y grupo tienen filtros combinables variables, por lo que construir SQL ad-hoc en cada endpoint genera duplicación difícil de mantener.

**Decisión:** Encapsular los criterios de filtrado en un Query Object reutilizable que construya la consulta según grupo, grado y docente autenticado.

**Consecuencias:**
- Permite combinar filtros sin duplicar lógica de consulta en endpoints.
- Facilita reutilizar criterios de filtrado en distintas partes del servicio.
- Requiere mantener los criterios sincronizados con el esquema de base de datos.

**Estado de implementación:** cumplido tras corrección de un hueco de seguridad real.
`PgStudentRepository.list_students()` no filtraba por docente propietario: cualquier
TEACHER/SPECIALIST podía listar alumnos de grupos ajenos. Se corrigió combinando
`is_privileged` (ADMIN/SPECIALIST sin restricción) con `g.teacher_id = :teacher_id`
para TEACHER, más filtro opcional por `grade` — mismo criterio replicado en
`PgGroupRepository.list_groups()`. Ver `infrastructure/database/repositories/pg_student_repository.py`
y `api/v1/students/router.py`.

---

### ADR-19 · Comando de Aplicación de Test
**Requerimiento:** HU-BK-05 — Servicio de aplicación de tests  
**Patrón:** Command (GoF)

**Contexto:** Enviar un test cerrado implica acciones encadenadas como guardar respuestas, validar pertenencia del alumno y disparar el microservicio de diagnóstico, y se requiere poder registrar, reintentar o auditar esa operación como una unidad.

**Decisión:** Encapsular el cierre y envío del test como un Command que ejecuta las acciones y dispara el diagnóstico de forma atómica.

**Consecuencias:**
- Permite reintentar el envío del test ante fallos sin duplicar lógica.
- Facilita auditar cada cierre de test como una operación discreta.
- Añade una clase adicional por cada tipo de comando que se soporte.

**Estado de implementación:** cumplido pragmáticamente. `SubmitAnswersUseCase.execute()`
en `application/use_cases/screening/submit_answers.py` ya encapsula la operación completa
como unidad ejecutable. Se decidió no renombrar a `SubmitAnswersCommand` ni agregar
`retry()`/`undo()` explícitos: el cliente HTTP ya maneja reintentos y deshacer una
respuesta guardada tiene implicaciones clínicas/de auditoría que no aplican aquí.

---

### ADR-20 · Observador de Estancamiento
**Requerimiento:** HU-BK-09 — Microservicio de seguimiento y alertas  
**Patrón:** Observer (GoF)

**Contexto:** El servicio de seguimiento calcula métricas de la curva de aprendizaje y debe notificar al módulo de alertas y al de recalibración cuando detecta estancamiento o mejora sostenida, sin acoplarse directamente a ninguno de ellos.

**Decisión:** Aplicar Observer para que el cálculo de métricas notifique a los suscriptores de alertas y recalibración ante cada cambio detectado.

**Consecuencias:**
- Desacopla el cálculo de métricas de las acciones que este desencadena.
- Permite agregar nuevos suscriptores sin modificar el cálculo base.
- Dificulta rastrear el orden exacto de notificaciones disparadas simultáneamente.

**Estado de implementación:** cumplido con Observer real (Subject GoF). Se introdujo
`EventBus` (`application/services/event_bus.py`, Singleton vía `get_event_bus()`) con
`subscribe`/`publish`. `PgTrackingRepository.evaluate_progress()` publica el evento
`ProgressEvaluated` (`domain/events/progress_evaluated.py`) en vez de llamar directo a
la creación de alertas; el suscriptor `create_alert_on_progress_evaluated`
(`application/services/alert_observer.py`) reacciona de forma desacoplada. Registrado
en `api/main.py` dentro de `lifespan()`. Corre dentro de la misma `AsyncSession` del
request para no romper la atomicidad del ADR-27.

---

### ADR-21 · Constructor de Reportes PDF
**Requerimiento:** HU-BK-10 — Microservicio de reportes PDF  
**Patrón:** Builder (GoF)

**Contexto:** El reporte PDF combina secciones variables como perfil disléxico, gráficas de evolución y recomendaciones que dependen del alumno y su historial, y ensamblarlas directamente con ReportLab en un solo método resulta rígido y difícil de mantener.

**Decisión:** Usar un Builder que ensamble el reporte PDF sección por sección a partir de los datos clínicos del alumno.

**Consecuencias:**
- Permite añadir o reordenar secciones del reporte sin reescribir todo.
- Facilita generar variantes del reporte para distintos destinatarios.
- Incrementa el número de clases necesarias para representar cada sección.

**Estado de implementación:** cumplido. `GenerateReportUseCase._render_pdf()` en
`application/use_cases/reports/generate_report.py` ensambla el PDF sección por sección
con ReportLab (encabezado, tabla de datos clínicos, ruta de ejercicios) según `report_type`.

---

### ADR-22 · Decorador de Caché Redis
**Requerimiento:** HU-BK-11 — Caché con Redis  
**Patrón:** Decorator (GoF)

**Contexto:** Las consultas a catálogos y perfiles frecuentes deben servirse desde Redis cuando estén disponibles, pero la lógica de caché no debe mezclarse con la lógica de negocio de cada servicio que consulta esos datos del sistema.

**Decisión:** Envolver las operaciones de consulta con un Decorator que intercepte la llamada y sirva desde Redis cuando el dato esté disponible.

**Consecuencias:**
- Añade comportamiento de caché sin modificar el servicio original.
- Permite activar o desactivar el caché de forma completamente transparente.
- Requiere gestionar cuidadosamente la invalidación al actualizar el dato fuente.

**Estado de implementación:** cumplido y conectado. `SemanticCache`
(`infrastructure/cache/semantic_cache.py`) existía pero no se usaba en ningún endpoint.
Se agregó el decorator `cached_endpoint` (`infrastructure/cache/cache_decorator.py`),
aplicado sobre los catálogos de referencia sin escritura en runtime:
`GET /screening/catalog`, `/screening/teacher-items`, `/screening/item-bank/tede`
(TTL 1h). Degrada con gracia a no-op si `REDIS_URL` no está configurado.

---

### ADR-23 · Registro Centralizado de Salud
**Requerimiento:** HU-BK-12 — Monitoreo de microservicios (Administrador)  
**Patrón:** Singleton (GoF)

**Contexto:** El panel de administración necesita una única fuente de verdad sobre el estado activo o caído de los ocho microservicios, consultando los endpoints /health sin crear múltiples instancias del registro de estado simultáneamente.

**Decisión:** Implementar un Singleton que centralice y exponga el estado de salud consolidado de todos los microservicios del sistema.

**Consecuencias:**
- Garantiza una única fuente consistente del estado del sistema.
- Simplifica la consulta del panel admin al depender de un solo componente.
- Puede convertirse en cuello de botella ante alta frecuencia de polling.

**Estado de implementación:** cumplido. `HealthRegistry`
(`infrastructure/pln/health_registry.py`), Singleton vía `get_health_registry()`
(`@lru_cache`, mismo patrón que los clientes PLN). `GET /health/pln` actualiza el
snapshot; `GET /health/pln/last-known` (nuevo) devuelve el último estado conocido
sin golpear la red — útil para polling frecuente de dashboards.

---

### ADR-24 · Estados de Versión del Modelo
**Requerimiento:** HU-BK-13 — Gestión de versiones del modelo (Administrador)  
**Patrón:** State (GoF)

**Contexto:** Cada versión del modelo de ML transita entre estados como en validación, en producción y retirado, y las acciones permitidas dependen del estado actual, lo que generaría condicionales repetidos sin un patrón estructurado.

**Decisión:** Modelar la versión del modelo con el patrón State, encapsulando las transiciones y las reglas válidas por cada estado posible.

**Consecuencias:**
- Evita condicionales extensos para validar transiciones entre estados.
- Impide estructuralmente activar versiones sin métricas validadas.
- Aumenta el número de clases necesarias para representar cada estado.

**Estado de implementación:** cumplido a nivel de invariante de datos, no como clases
State en Python. `PgModelVersionRepository.activate()` más un `CHECK constraint` de
PostgreSQL en `diagnosis.ml_model_versions` bloquean la transición inválida
(`IntegrityError`, capturado en `api/v1/admin/router.py`). Se decidió no agregar
`VersionInValidation`/`VersionInProduction`/`VersionRetired` en código: el estado real
es un solo booleano (`is_production`) sin comportamiento condicional adicional que
justifique el patrón OOP — el constraint de BD ya es la fuente de verdad correcta.

---

### ADR-25 · Decorador de Auditoría de Acciones
**Requerimiento:** HU-BK-14 — Logs y auditoría  
**Patrón:** Decorator (GoF)

**Contexto:** Las acciones críticas del sistema deben generar un log inmutable con usuario, acción y timestamp, pero esta responsabilidad transversal no debe mezclarse con la lógica de negocio propia de cada operación de los microservicios.

**Decisión:** Envolver las operaciones críticas con un Decorator que registre el log antes o después de ejecutar la acción principal correspondiente.

**Consecuencias:**
- Separa la lógica de auditoría de la lógica de negocio principal.
- Facilita aplicar logging consistente a múltiples operaciones del sistema.
- Añade una capa de indirección sobre cada llamada que requiere auditoría.

**Estado de implementación:** cumplido con Decorator real. `AuditLogger().log(...)` se
llamaba manualmente y repetido en 6 routers. Se introdujo `audited()`
(`security/audit/audit_decorator.py`) que envuelve el endpoint y registra el evento tras
un retorno exitoso, soportando `target_id_arg`/`target_id_fn`, `metadata_fn` y `condition`
(para auditar solo cuando aplica, ej. `evaluate_progress` solo si se generó alerta).
Aplicado en `students`, `screening`, `reports`, `admin`, `groups` y `tracking`. Se dejó
sin automatizar `auth/router.py` (timing irregular de `user` antes de login completo) y
`security/router.py` (`write_audit_event` es el propio mecanismo manual expuesto a
ADMIN/SPECIALIST).

---

### ADR-26 · Repositorio de Usuarios y Roles
**Requerimiento:** HU-BD-01 — Modelo de usuarios y roles  
**Patrón:** Repository (Fowler)

**Contexto:** El esquema de usuarios con rol debe garantizar correo único, hash Argon2 y catálogo restringido de roles, y el acceso a esta tabla debe encapsularse para evitar consultas SQL dispersas por todo el backend del sistema.

**Decisión:** Encapsular el acceso a la tabla de usuarios mediante un Repository que centralice las reglas de unicidad, rol y eliminación lógica.

**Consecuencias:**
- Centraliza las validaciones de correo único y catálogo de roles.
- Facilita cambiar el motor de persistencia sin afectar a los consumidores.
- Agrega una capa intermedia sobre operaciones de base de datos simples.

**Estado de implementación:** cumplido — mismo `UserRepository` documentado en ADR-17.

---

### ADR-27 · Unidad de Trabajo para Tests
**Requerimiento:** HU-BD-03 — Tests diagnósticos y respuestas originales  
**Patrón:** Unit of Work (Fowler)

**Contexto:** Guardar un test implica insertar el registro del test y sus respuestas originales de forma atómica, y un fallo parcial dejaría datos inconsistentes que comprometerían la evidencia usada por el pipeline de PLN/ML.

**Decisión:** Aplicar Unit of Work para agrupar la inserción del test y sus respuestas en una sola transacción atómica e indivisible.

**Consecuencias:**
- Garantiza consistencia entre el test y sus respuestas asociadas.
- Simplifica el manejo de errores ante fallos parciales de escritura.
- Requiere coordinar explícitamente el ciclo de vida de la transacción.

**Estado de implementación:** cumplido vía sesión SQLAlchemy por request, no una clase
`UnitOfWork` explícita. `get_db()` (`api/dependencies/database.py`) hace un solo
`commit()` al final del request; como todas las escrituras de un endpoint comparten esa
misma `AsyncSession`, la atomicidad se logra sin infraestructura adicional.

---

## Alicia — Aplicación Móvil Flutter (ADR-28 a ADR-40)

---

### ADR-28 · Decorador de Pantalla Segura
**Requerimiento:** HU-FL-01 — Inicio de sesión seguro + bloqueo de capturas  
**Patrón:** Decorator (GoF)

**Contexto:** Las pantallas que muestran datos clínicos de menores deben activar FLAG_SECURE para bloquear capturas, mientras que otras pantallas de la app no requieren esa restricción, evitando duplicar la configuración en cada widget clínico.

**Decisión:** Envolver las pantallas sensibles con un Decorator que active FLAG_SECURE sin modificar el widget base subyacente.

**Consecuencias:**
- Permite activar la protección solo en pantallas que realmente lo necesitan.
- Evita duplicar configuración de seguridad en cada pantalla clínica.
- Exige recordar aplicar el decorador en cada nueva pantalla sensible que se agregue.

---

### ADR-29 · Adaptador de Cliente de Alumnos
**Requerimiento:** HU-FL-02 — Gestión de alumnos por grupo y grado (Docente)  
**Patrón:** Adapter (GoF)

**Contexto:** La app Flutter consume el endpoint de alumnos del backend mediante Dio, y la UI necesita trabajar con modelos propios de la app en lugar de acoplarse directamente al formato JSON crudo devuelto por la API.

**Decisión:** Implementar un Adapter que transforme la respuesta de la API en los modelos de dominio usados internamente por la UI de Flutter.

**Consecuencias:**
- Aísla la UI de cambios en el contrato del backend de alumnos.
- Facilita testear la pantalla con datos simulados desacoplados de la API.
- Añade una capa de transformación adicional por cada respuesta recibida.

---

### ADR-30 · Comando de Asignación de Test
**Requerimiento:** HU-FL-03 — Asignación de test diagnóstico (Docente)  
**Patrón:** Command (GoF)

**Contexto:** Asignar un test implica seleccionar alumno y tipo, confirmar la acción y enviarla al backend, y la app necesita poder reintentar el envío o deshacer la confirmación sin duplicar lógica dispersa en la pantalla.

**Decisión:** Encapsular la asignación de test como un Command ejecutable que la pantalla invoca tras la confirmación explícita del docente.

**Consecuencias:**
- Permite reintentar el envío sin duplicar lógica de validación en la pantalla.
- Facilita probar la asignación de test de forma completamente aislada.
- Introduce una clase adicional para una operación relativamente simple.

---

### ADR-31 · Fachada del Perfil Clínico
**Requerimiento:** HU-FL-04 — Consulta del perfil clínico (Docente)  
**Patrón:** Facade (GoF)

**Contexto:** Mostrar el perfil del alumno requiere combinar datos de diagnóstico, historial de evaluaciones y nivel de riesgo de distintos microservicios, y la pantalla no debería coordinar múltiples llamadas HTTP de forma directa.

**Decisión:** Exponer una Facade en la capa de datos que combine las llamadas necesarias y entregue el perfil del alumno ya unificado.

**Consecuencias:**
- Simplifica la pantalla al consumir una única fuente de datos consolidada.
- Oculta a la UI los detalles de los microservicios involucrados en el perfil.
- Centraliza el manejo de errores de las múltiples llamadas que se combinan.

---

### ADR-32 · Observador de la Curva de Aprendizaje
**Requerimiento:** HU-FL-05 — Curva de aprendizaje y seguimiento (Docente)  
**Patrón:** Observer (GoF)

**Contexto:** La gráfica de evolución debe actualizarse reactivamente cuando cambian el rango temporal seleccionado o llegan nuevas métricas, y Riverpod gestiona el estado de forma que los widgets necesitan reaccionar automáticamente a esos cambios.

**Decisión:** Usar el patrón Observer mediante providers de Riverpod para que la gráfica reaccione a cambios en las métricas disponibles.

**Consecuencias:**
- Mantiene la gráfica sincronizada automáticamente con el estado actual.
- Evita lógica manual de refresco dentro del widget de visualización.
- Requiere cuidado para evitar reconstrucciones innecesarias de la UI.

---

### ADR-33 · Observador de Alertas Push
**Requerimiento:** HU-FL-06 — Alertas de estancamiento (Docente)  
**Patrón:** Observer (GoF)

**Contexto:** La bandeja de alertas debe reflejar nuevas alertas de estancamiento emitidas por el backend, y distintos widgets como el indicador y la bandeja necesitan enterarse del mismo cambio sin sondear el servidor constantemente.

**Decisión:** Aplicar Observer sobre el estado de alertas para que el indicador y la bandeja se actualicen ante cualquier cambio de estado.

**Consecuencias:**
- Mantiene sincronizados varios widgets que dependen del mismo estado.
- Evita peticiones repetidas de sondeo manual al backend.
- Depende de un mecanismo de notificación o polling subyacente confiable.

---

### ADR-34 · Proxy de Descarga de Reportes
**Requerimiento:** HU-FL-07 — Generación y descarga de reportes PDF (Docente)  
**Patrón:** Proxy (GoF)

**Contexto:** Descargar el reporte PDF puede tardar y el docente podría solicitarlo varias veces para el mismo alumno en una sesión, por lo que conviene controlar el acceso al archivo remoto sin descargarlo repetidamente de forma innecesaria.

**Decisión:** Implementar un Proxy que controle la descarga del PDF, mostrando indicador de progreso y evitando llamadas redundantes al servicio.

**Consecuencias:**
- Evita descargas duplicadas del mismo reporte dentro de una sesión.
- Centraliza el manejo de progreso y errores de la descarga del PDF.
- Añade complejidad si se requiere invalidar el proxy ante reportes nuevos.

---

### ADR-35 · Estrategias de Accesibilidad Visual
**Requerimiento:** HU-FL-09 — Interfaz simplificada y multisensorial (Alumno)  
**Patrón:** Strategy (GoF)

**Contexto:** La interfaz del alumno debe adaptar tipografía, contraste e iconografía según el perfil disléxico detectado, y estas variaciones de presentación deben intercambiarse sin reescribir las pantallas de ejercicios para cada combinación posible.

**Decisión:** Encapsular las reglas de presentación accesible como estrategias intercambiables seleccionadas dinámicamente según el perfil del alumno.

**Consecuencias:**
- Permite ajustar la presentación visual sin modificar las pantallas base.
- Facilita agregar nuevos perfiles de accesibilidad en el futuro.
- Exige mantener consistencia visual entre las distintas estrategias definidas.

---

### ADR-36 · Adaptador de TTS/STT
**Requerimiento:** HU-FL-10 — Ejercicios de diagnóstico (Alumno)  
**Patrón:** Adapter (GoF)

**Contexto:** Los ejercicios de dictado y lectura dependen de plugins nativos de TTS y STT cuyas APIs varían entre Android e iOS, y la app necesita una interfaz uniforme para invocarlos desde la lógica de ejercicios sin condicionales de plataforma.

**Decisión:** Definir un Adapter que unifique las APIs nativas de TTS/STT bajo una interfaz común usada por todos los ejercicios multisensoriales.

**Consecuencias:**
- Aísla la lógica de ejercicios de las diferencias entre plataformas móviles.
- Facilita sustituir el plugin de voz sin afectar el resto de la app.
- Requiere mantener el adaptador actualizado ante cambios en las APIs nativas.

---

### ADR-37 · Estados del Ejercicio Dinámico
**Requerimiento:** HU-FL-11 — Ejercicios de intervención dinámica (Alumno)  
**Patrón:** State (GoF)

**Contexto:** El tipo y dificultad del ejercicio mostrado cambian en tiempo real según el desempeño del alumno, y cada estado de la ruta activa habilita transiciones y comportamientos distintos en la pantalla de ejercicios interactivos.

**Decisión:** Modelar el ejercicio activo con el patrón State para encapsular el comportamiento y las transiciones según el desempeño registrado.

**Consecuencias:**
- Estructura claramente las transiciones entre tipos de ejercicio disponibles.
- Evita condicionales extensos dentro de la pantalla de ejercicios.
- Incrementa el número de clases necesarias para representar cada estado.

---

### ADR-38 · Observador de Eventos de Error
**Requerimiento:** HU-FL-12 — Retroalimentación inmediata (Alumno)  
**Patrón:** Observer (GoF)

**Contexto:** Al cometer un error disléxico específico, varios elementos de la UI deben reaccionar simultáneamente como parpadeo de la letra y refuerzo por voz, y acoplar esa reacción al detector de errores dificultaría agregar nuevas reacciones futuras.

**Decisión:** Emitir el evento de error mediante Observer para que los widgets visuales y de audio reaccionen de forma completamente independiente.

**Consecuencias:**
- Permite agregar nuevas formas de retroalimentación sin tocar el detector.
- Mantiene desacoplada la lógica de detección de la de presentación.
- Requiere cuidado para evitar reacciones duplicadas ante el mismo evento.

---

### ADR-39 · Memento del Estado del Ejercicio
**Requerimiento:** HU-FL-13 — Persistencia local y modo sin conexión  
**Patrón:** Memento (GoF)

**Contexto:** Si se pierde la conexión durante un ejercicio, el progreso del alumno debe conservarse localmente y restaurarse al reconectar, sin exponer la estructura interna del estado del ejercicio a otros componentes de la aplicación móvil.

**Decisión:** Usar Memento para capturar y restaurar el estado del ejercicio en almacenamiento local ante pérdida de conexión.

**Consecuencias:**
- Permite reanudar el ejercicio exacto donde se interrumpió la conexión.
- Evita exponer la estructura interna del estado a otros módulos de la app.
- Requiere gestionar la expiración de mementos no sincronizados con el backend.

---

### ADR-40 · Decorador de Interceptores HTTP
**Requerimiento:** HU-FL-14 — Comunicación con el backend (Dio)  
**Patrón:** Decorator (GoF)

**Contexto:** Cada petición HTTP del cliente Dio necesita comportamientos adicionales como adjuntar el JWT, reintentar fallos transitorios y aplicar timeouts, y mezclar todo en una sola función dificultaría modificar un comportamiento sin afectar los demás.

**Decisión:** Implementar cada comportamiento de red como un interceptor-decorador independiente que envuelve las peticiones del cliente Dio.

**Consecuencias:**
- Permite activar o desactivar comportamientos de red de forma independiente.
- Facilita agregar nuevos interceptores sin modificar los ya existentes.
- El orden de los interceptores debe gestionarse con cuidado en la configuración.
