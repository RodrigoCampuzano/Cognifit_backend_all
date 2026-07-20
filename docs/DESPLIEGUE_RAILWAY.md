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

## La causa real

**Los servicios nunca arrancaron.** Estaban en bucle de reinicio, y los logs lo
dicen sin ambigüedad:

```
$ railway logs --service diagnosis
Error: Invalid value for '--port': '$PORT' is not a valid integer.
Usage: uvicorn [OPTIONS] APP
Error: Invalid value for '--port': '$PORT' is not a valid integer.
...
```

Hay un **comando de inicio personalizado** configurado en Railway que pasa
`--port $PORT` sin que un shell expanda la variable, así que uvicorn recibe la
cadena literal `$PORT` y muere al arrancar.

La variable existe y tiene el valor correcto:

```
$ railway variables --service diagnosis
PORT                   │ 8001
RAILWAY_PRIVATE_DOMAIN │ diagnosis.railway.internal
```

### Una hipótesis previa que resultó equivocada

El primer diagnóstico atribuyó la caída a que los servicios escuchaban en IPv4
mientras la red privada de Railway es IPv6. El razonamiento partía de que el
campo `error` llegaba vacío, lo que corresponde a `ConnectTimeout`, y de ahí se
concluyó que el proceso estaba vivo pero inalcanzable.

La conclusión no se sostiene: **un contenedor en bucle de reinicio produce el
mismo síntoma**, porque los paquetes hacia un contenedor muerto se descartan en
vez de rechazarse. El tiempo agotado no distinguía entre "escucha en la
interfaz equivocada" y "no escucha en absoluto".

Lo que faltó fue mirar los logs del servicio antes de teorizar. El cambio a
IPv6 se conserva porque es necesario igual para la red privada de Railway,
pero por sí solo no habría arreglado nada.

## Las correcciones

### 1. El puerto sale de `PORT`, dentro de un shell

```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host \"$BIND_HOST\" --port \"${PORT:-8001}\""]
```

La forma `sh -c` es lo que permite expandir las variables. En forma exec llegan
literales, que es justo el fallo original.

### 2. La interfaz por defecto es `::`

```dockerfile
ENV BIND_HOST=::
```

| Entorno | Valor | Quién lo define |
|---|---|---|
| Railway | `::` | el `Dockerfile` (por defecto) |
| `docker-compose` | `0.0.0.0` | `docker-compose.yml` |

El defecto es `::` a propósito: Railway se despliega desde el `Dockerfile` sin
nada más, así que el entorno que no se puede configurar es el que tiene que
funcionar solo.

## Qué hay que hacer en Railway

**Quitar el comando de inicio personalizado** de los servicios `diagnosis` y
`recommendation`, en *Settings → Deploy → Custom Start Command*. Al dejarlo
vacío se usa el `CMD` del `Dockerfile`, que ya expande las variables
correctamente.

Mientras ese comando siga configurado, sobrescribe al `Dockerfile` y los
servicios seguirán sin arrancar por más que se redespliegue.

Después, verificar:

```bash
curl -s https://<tu-api>.up.railway.app/api/v1/health/pln
railway logs --service diagnosis      # debe decir "Uvicorn running on http://[::]:8001"
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
