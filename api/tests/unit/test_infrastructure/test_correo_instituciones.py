"""Avisos por correo del alta de una escuela.

Antes solo se avisaba al SUPERADMIN cuando llegaba una solicitud. Quien
registraba su escuela quedaba a ciegas en los dos extremos: no sabía si la
solicitud había llegado, y tampoco cuándo quedaba aprobada. Como la cuenta no
puede iniciar sesión hasta la aprobación, no tenía forma de comprobarlo dentro
de la app: el único camino era reintentar el login cada tanto.
"""
import inspect

from api.v1.institutions import router as mod


def _fuente(func) -> str:
    return inspect.getsource(func)


def test_al_solicitar_se_avisa_al_superadmin():
    src = _fuente(mod.register_institution)
    assert "notification_email_to" in src


def test_al_solicitar_se_le_confirma_a_quien_solicita():
    src = _fuente(mod.register_institution)
    assert "to=payload.admin_email" in src, (
        "el solicitante debe recibir acuse de recibo"
    )


def test_el_acuse_avisa_que_todavia_no_podra_entrar():
    """Es la pregunta que el usuario se hace enseguida: registró la escuela y
    el login le falla. Sin esta línea parece un error del sistema."""
    src = _fuente(mod.register_institution)
    assert "no vas a poder iniciar sesión" in src


def test_al_aprobar_se_avisa_al_admin():
    src = _fuente(mod.approve_institution)
    assert "admin_email(institution_id)" in src
    assert "background_tasks.add_task" in src


def test_los_correos_van_en_segundo_plano():
    """Si el envío fuera sincrónico, un SMTP lento dejaría al docente
    esperando en una pantalla de registro, y uno caído devolvería un error
    para una operación que sí se completó."""
    for func in (mod.register_institution, mod.approve_institution):
        assert "background_tasks.add_task" in _fuente(func)


def test_una_aprobacion_sin_admin_no_falla():
    """El registro siempre crea un ADMIN, así que no encontrarlo es una
    inconsistencia; aun así la aprobación ya ocurrió y no debe revertirse por
    no poder avisar."""
    src = _fuente(mod.approve_institution)
    i = src.index("if destinatario:")
    assert "logger.warning" in src[i:], "debe registrarse, no romper"
    assert "return approved" in src[i:]


def test_las_credenciales_no_estan_en_el_codigo():
    """Deben venir del entorno: el repositorio es público."""
    from config.settings import Settings

    for campo in ("smtp_user", "smtp_password", "smtp_host"):
        assert Settings.model_fields[campo].default is None, (
            f"{campo} no debe traer un valor por defecto en el código"
        )


def test_sin_smtp_configurado_el_envio_se_omite_sin_romper():
    """Permite correr en desarrollo y en las pruebas sin servidor de correo."""
    import asyncio

    from infrastructure.email.smtp_email_service import SmtpEmailService

    svc = SmtpEmailService()
    svc.settings.smtp_host = None
    asyncio.run(svc.send(to="x@y.mx", subject="s", body="b"))


# ─── Rechazo ─────────────────────────────────────────────────────────────────
# Antes una solicitud tenía dos salidas de hecho: aprobada o pendiente para
# siempre. Una escuela ilegítima o duplicada quedaba en /pending sin caducar y
# su autor nunca recibía respuesta.


def test_existe_endpoint_de_rechazo():
    assert hasattr(mod, "reject_institution")


def test_al_rechazar_se_avisa_con_el_motivo():
    src = _fuente(mod.reject_institution)
    assert "admin_email(institution_id)" in src
    assert "background_tasks.add_task" in src
    assert "payload.reason" in src, "el motivo debe viajar al correo"


def test_una_solicitud_ya_resuelta_da_404():
    """El repositorio solo rechaza pendientes; el endpoint traduce el None a
    404. Distinguir 'no existe' de 'ya resuelta' filtraría el estado de
    escuelas ajenas."""
    src = _fuente(mod.reject_institution)
    assert "status_code=404" in src


def test_el_filtro_de_pendientes_excluye_las_rechazadas():
    """Sin esto una rechazada volvería a /pending en cada carga: list_pending
    filtra por is_active = FALSE, que también cumple una rechazada."""
    from infrastructure.database.repositories.pg_institution_repository import (
        PgInstitutionRepository,
    )

    sql = inspect.getsource(PgInstitutionRepository.list_pending)
    assert "rejected_at IS NULL" in sql


def test_reject_solo_actua_sobre_pendientes():
    """El WHERE del UPDATE impide desactivar una escuela ya aprobada por un
    rechazo tardío."""
    from infrastructure.database.repositories.pg_institution_repository import (
        PgInstitutionRepository,
    )

    sql = inspect.getsource(PgInstitutionRepository.reject)
    assert "is_active = FALSE" in sql
    assert "rejected_at IS NULL" in sql
