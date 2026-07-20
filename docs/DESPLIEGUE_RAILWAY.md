# Despliegue en Railway — servicios de PLN

## El síntoma

`GET /api/v1/health/pln` devuelve:

```json
{
  "status": "degraded",
  "diagnosis":      {"status": "down", "error": ""},
  "recommendation": {"status": "down", "error": ""}
}
```

El API responde bien, pero los dos microservicios de PLN aparecen caídos. En la
aplicación esto se ve como un error al abrir comprensión lectora, y además
impide que el tamizaje genere diagnósticos.

## La causa

**El campo `error` vacío es la pista.** Se reprodujo cada modo de falla para
identificarlo:

| Situación | `str(exc)` |
|---|---|
| Nada escuchando en el puerto | `'All connection attempts failed'` |
| El host no resuelve | `'[Errno -3] Temporary failure in name resolution'` |
| **La conexión agota el tiempo** | **`''`** |

Un mensaje vacío corresponde a `ConnectTimeout`: el nombre **sí** resuelve y el
servicio **sí** está desplegado, pero nadie responde.

Eso ocurre porque la red privada de Railway es **IPv6**, y los servicios estaban
enlazados a `0.0.0.0`, que atiende **solo IPv4**. La conexión sale, no encuentra
a nadie escuchando en IPv6 y se queda esperando hasta agotar el tiempo — en vez
de ser rechazada de inmediato.

Referencia: <https://docs.railway.com/private-networking>

## La corrección

Los `Dockerfile` de ambos servicios aceptan `BIND_HOST`, y **el valor por
defecto es `::`**:

```dockerfile
ENV BIND_HOST=::
CMD ["sh", "-c", "uvicorn app.main:app --host \"$BIND_HOST\" --port 8002"]
```

No existe un valor único que sirva en los dos entornos:

| Entorno | Valor | Quién lo define |
|---|---|---|
| Railway | `::` | el propio `Dockerfile` (por defecto) |
| `docker-compose` local | `0.0.0.0` | `docker-compose.yml` |

El defecto es `::` a propósito. Railway se despliega desde el `Dockerfile` sin
nada más, así que **el entorno que no se puede configurar solo es el que tiene
que funcionar solo**. `docker-compose` sí puede fijar el suyo, y lo hace.

Se comprobó que enlazar a `::` sin más **rompe** el entorno local: los
contenedores dejan de alcanzarse entre sí porque la red de Docker es IPv4. De
ahí que el compose fije `0.0.0.0` explícitamente.

## Qué hay que hacer en Railway

**Solo redesplegar.** No hace falta agregar ninguna variable: la imagen ya trae
el valor correcto.

Conviene comprobar que estas dos sigan apuntando a los internos, porque su
valor por defecto es `localhost` y ahí no hay nada:

```
DIAGNOSIS_SERVICE_URL=http://diagnosis.railway.internal:8001
RECOMMENDATION_SERVICE_URL=http://recommendation.railway.internal:8002
```

## El fallo silencioso que esto provocaba

Con `PLN_FALLBACK_ENABLED=true`, un servicio de diagnóstico caído **no produce
un error**: el API recurre a un pipeline local de respaldo y guarda igual el
resultado. En la base quedó registrado con `pln_source = 'local_fallback'`.

El efecto es que el docente ve un diagnóstico de aspecto normal que **no lo
hizo el modelo entrenado**. Es una falla peor que una visible, porque no
interrumpe a nadie.

La aplicación marca esos casos en el perfil del alumno. Al revisar cualquier
diagnóstico anterior, los que digan `local_fallback` conviene repetirlos una vez
que `/api/v1/health/pln` responda `"ok"`.

## Cómo verificar que quedó

```bash
curl -s https://<tu-api>.up.railway.app/api/v1/health/pln
```

Debe responder `"status": "ok"` con ambos servicios en `"ok"`. Mientras alguno
siga en `"down"`, ni la comprensión lectora ni el diagnóstico funcionan.
