# Rotar los secretos de producción

Cuatro secretos quedaron expuestos y hay que reemplazarlos. Tres se cambian
solo en Railway; el de cifrado necesita un paso previo.

| Secreto | Qué permite si alguien lo tiene | Cómo se rota |
|---|---|---|
| `JWT_SECRET_KEY` | Falsificar tokens de cualquier usuario, incluido ADMIN | Variable |
| `PASSWORD_PEPPER` | Debilita el hash de todas las contraseñas | Variable |
| Contraseña de Neon | Acceso directo a la base | Panel de Neon + variable |
| `DB_ENCRYPTION_KEY` | Descifrar los nombres de los alumnos | **Script + variable** |

## El de cifrado es distinto

Los datos guardados están cifrados **con** esa clave. Cambiar la variable sin
más deja los nombres ilegibles de forma permanente: no hay manera de
recuperarlos. Primero hay que descifrar con la vieja y volver a cifrar con la
nueva, y recién después cambiar la variable.

Entre esos dos pasos la aplicación no puede leer los nombres. Van seguidos, y
conviene hacerlo fuera de horario de clase.

### 1. Generar la clave nueva

```bash
python3 -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

Guardarla en un gestor de contraseñas, no en un archivo del proyecto ni en un
chat.

### 2. Simular

El script no necesita correr en Railway: se conecta a Neon directamente. Se usa
`railway run` solo para que inyecte las variables y no haya que teclear ningún
secreto — que es exactamente cómo se filtraron la primera vez.

```bash
CLAVE_NUEVA="<la del paso 1>" \
  railway run --service api -- python api/scripts/rotar_clave_cifrado.py
```

Sin `--aplicar` no escribe nada. Debe informar cuántas filas se leen con la
clave vieja.

Si no hay `asyncpg` en la máquina, se corre dentro del contenedor local:

```bash
docker compose exec \
  -e SYNC_DATABASE_URL="$(railway variables -s api -k | grep ^SYNC_DATABASE_URL= | cut -d= -f2-)" \
  -e DB_ENCRYPTION_KEY="$(railway variables -s api -k | grep ^DB_ENCRYPTION_KEY= | cut -d= -f2-)" \
  -e CLAVE_NUEVA="<la del paso 1>" \
  api python /app/scripts/rotar_clave_cifrado.py
```

### 3. Aplicar

```bash
CLAVE_NUEVA="<la misma>" \
  railway run --service api -- python api/scripts/rotar_clave_cifrado.py --aplicar
```

Todo ocurre en una transacción y se verifica antes de confirmar: si alguna fila
no se lee con la clave nueva, revierte y no queda nada a medias.

### 4. Cambiar la variable, enseguida

```bash
railway variables set -s api DB_ENCRYPTION_KEY="<la del paso 1>"
```

### 5. Comprobar

```bash
curl -s https://<api>.up.railway.app/api/v1/health
```

Y abrir el perfil de un alumno en la aplicación: si el nombre se ve bien, quedó.
Si aparece vacío o con error, la variable no coincide con la clave usada al
recifrar.

## Los otros tres

```bash
# Claves nuevas
python3 -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(48)).decode())"

railway variables set -s api JWT_SECRET_KEY="<nueva>"
railway variables set -s api PASSWORD_PEPPER="<nueva>"
```

**`JWT_SECRET_KEY` cierra todas las sesiones abiertas**: cada usuario vuelve a
iniciar sesión. Con la cantidad actual de usuarios no es problema.

**`PASSWORD_PEPPER` merece atención**: se usa al derivar la contraseña, así que
cambiarlo invalida los hashes existentes y nadie podría entrar. Conviene
revisar cómo lo aplica `argon2` en este proyecto antes de tocarlo, o
restablecer las contraseñas después.

La de Neon se cambia en su panel y después en Railway:

```bash
railway variables set -s api DATABASE_URL="postgresql+asyncpg://...nueva..."
railway variables set -s api SYNC_DATABASE_URL="postgresql://...nueva..."
```

## Después de rotar

Comprobar que no quedaron copias:

```bash
grep -rn "<fragmento de la clave vieja>" ~/.bash_history .env* 2>/dev/null
git log --all -S "<fragmento>" --oneline
```

En este repo ya se verificó que **ninguno de los cuatro estuvo versionado**, que
es lo único irreversible.
