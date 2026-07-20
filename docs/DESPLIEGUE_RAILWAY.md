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

Los `Dockerfile` de ambos servicios aceptan ahora `BIND_HOST`:

```dockerfile
ENV BIND_HOST=0.0.0.0
CMD ["sh", "-c", "uvicorn app.main:app --host \"$BIND_HOST\" --port 8002"]
```

No existe un valor único que sirva en los dos entornos, y por eso es variable:

| Entorno | Valor | Motivo |
|---|---|---|
| `docker-compose` local | `0.0.0.0` (por defecto) | la red de Docker es IPv4 |
| Railway | `::` | la red privada es IPv6 |

Se comprobó que enlazar solo a `::` **rompe** el entorno local: los contenedores
dejan de alcanzarse entre sí. Por eso el valor por defecto es `0.0.0.0` y el
cambio se hace únicamente en Railway.

## Qué hay que configurar en Railway

En **cada uno** de los dos servicios de PLN, agregar la variable:

```
BIND_HOST=::
```

Y en el servicio del **API**, comprobar que apunte a los internos:

```
DIAGNOSIS_SERVICE_URL=http://<servicio-diagnosis>.railway.internal:8001
RECOMMENDATION_SERVICE_URL=http://<servicio-recommendation>.railway.internal:8002
```

El valor por defecto de esas dos variables es `http://localhost:8002`, que
dentro de un contenedor de Railway no apunta a nada.

## Cómo verificar que quedó

```bash
curl -s https://<tu-api>.up.railway.app/api/v1/health/pln
```

Debe responder `"status": "ok"` con ambos servicios en `"ok"`. Mientras alguno
siga en `"down"`, ni la comprensión lectora ni el diagnóstico funcionan.
