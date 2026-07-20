# Correo: avisos del alta de escuelas

## Qué se envía

| Momento | Destinatario | Contenido |
|---|---|---|
| Se solicita una escuela | **SUPERADMIN** (`NOTIFICATION_EMAIL_TO`) | datos de la escuela y del admin, para revisar |
| Se solicita una escuela | **el admin que registró** | acuse de recibo y aviso de que todavía no puede entrar |
| Se aprueba la escuela | **el admin que registró** | ya puede iniciar sesión |

Los dos últimos no existían: quien registraba su escuela quedaba a ciegas en
ambos extremos. Como la cuenta no puede iniciar sesión hasta la aprobación, no
tenía forma de comprobarlo dentro de la app — el único camino era reintentar el
login cada tanto hasta que funcionara.

## Variables de entorno

Ninguna credencial vive en el código. Se configuran en Railway:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<cuenta desde la que se envía>
SMTP_PASSWORD=<contraseña de aplicación, NO la del correo>
EMAIL_FROM=CogniFit Escolar <no-reply@tudominio.mx>
NOTIFICATION_EMAIL_TO=<correo que recibe las solicitudes nuevas>
```

`EMAIL_FROM` es opcional: si falta se usa `SMTP_USER`.

### Con Gmail

Gmail no acepta la contraseña de la cuenta desde una aplicación. Hay que
generar una **contraseña de aplicación**, que requiere tener activada la
verificación en dos pasos:

<https://myaccount.google.com/apppasswords>

Esa contraseña de 16 caracteres es la que va en `SMTP_PASSWORD`. Se puede
revocar sin cambiar la contraseña de la cuenta, que es la razón de usarla.

```bash
railway variables set -s api SMTP_HOST=smtp.gmail.com
railway variables set -s api SMTP_PORT=587
railway variables set -s api SMTP_USER="cuenta@gmail.com"
railway variables set -s api SMTP_PASSWORD="xxxx xxxx xxxx xxxx"
railway variables set -s api NOTIFICATION_EMAIL_TO="tu-correo@gmail.com"
```

## Qué pasa si no está configurado

Nada se rompe. `SmtpEmailService` devuelve sin hacer nada cuando `SMTP_HOST`
está vacío, así que el registro y la aprobación funcionan igual — solo que sin
aviso. Eso permite trabajar en desarrollo y correr las pruebas sin servidor de
correo.

Y si el SMTP está configurado pero falla, la excepción se registra en el log y
la operación de negocio continúa: **no se pierde un alta de escuela porque el
correo esté caído**. Los envíos van además en segundo plano, así que un
servidor lento no deja al docente esperando en la pantalla de registro.

## Verificar que funciona

```bash
railway logs --service api | grep -i "correo"
```

Un envío fallido aparece como `Falló el envío de correo a <destinatario>`. Si
no aparece nada y tampoco llega el correo, probablemente `SMTP_HOST` esté
vacío y los avisos se estén omitiendo en silencio.

## Rechazo

`POST /institutions/{id}/reject` (solo SUPERADMIN) marca una solicitud como
rechazada y avisa por correo al solicitante, con el motivo si se envía uno en
el cuerpo (`{"reason": "..."}`, opcional). Una vez rechazada deja de aparecer
en `/pending`, y no puede volver a rechazarse ni desactiva una escuela ya
aprobada.
