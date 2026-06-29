"""Pruebas del pipeline de cifrado en reposo / descifrado en uso (entregable #4)."""
from __future__ import annotations

import pytest

from security.encryption.pipeline.example_persona import Persona
from security.encryption.pipeline.interceptor import PersistenceInterceptor
from security.encryption.pipeline.key_provider import LocalKeyProvider
from security.encryption.pipeline.metadata_engine import MetadataEngine
from security.encryption.pipeline.pipes.cipher_pipe import CipherPipe
from security.encryption.pipeline.pipes.decrypt_pipe import DecryptPipe


def _interceptor() -> PersistenceInterceptor:
    engine = MetadataEngine()
    keys = LocalKeyProvider(master_key="clave-maestra-de-prueba-32bytes!!", require_strong=False)
    return PersistenceInterceptor(engine, CipherPipe(engine, keys), DecryptPipe(engine, keys))


def _persona() -> Persona:
    return Persona(
        nombres="María Fernanda",
        apellidos="Pérez López",
        nss="12345678901",
        fecha_nacimiento="2017-05-03",
        edad=8,
        rol_familiar="hija",
    )


def test_cifra_en_reposo_solo_campos_sensibles():
    interceptor = _interceptor()
    at_rest = interceptor.prepare_for_write(_persona(), scope="personas")

    # Sensibles → cifrados (prefijo enc::)
    assert at_rest.nombres.startswith("enc::")
    assert at_rest.apellidos.startswith("enc::")
    assert at_rest.nss.startswith("enc::")
    # No sensibles → en claro
    assert at_rest.edad == 8
    assert at_rest.rol_familiar == "hija"
    # El ciphertext no contiene el texto original
    assert "María" not in at_rest.nombres


def test_descifra_en_uso_round_trip():
    interceptor = _interceptor()
    at_rest = interceptor.prepare_for_write(_persona(), scope="personas")
    in_use = interceptor.materialize_from_read(at_rest, scope="personas")

    assert in_use.nombres == "María Fernanda"
    assert in_use.apellidos == "Pérez López"
    assert in_use.nss == "12345678901"


def test_no_muta_el_objeto_original():
    interceptor = _interceptor()
    original = _persona()
    interceptor.prepare_for_write(original, scope="personas")
    assert original.nombres == "María Fernanda"  # el caller conserva su objeto intacto


def test_idempotente_no_recifra():
    interceptor = _interceptor()
    once = interceptor.prepare_for_write(_persona(), scope="personas")
    twice = interceptor.prepare_for_write(once, scope="personas")
    assert once.nombres == twice.nombres  # no se cifra dos veces


def test_scope_incorrecto_falla_al_descifrar():
    interceptor = _interceptor()
    at_rest = interceptor.prepare_for_write(_persona(), scope="personas")
    with pytest.raises(ValueError):
        interceptor.materialize_from_read(at_rest, scope="otra_tabla")


def test_clave_insegura_en_produccion_es_rechazada():
    with pytest.raises(RuntimeError):
        LocalKeyProvider(master_key=None, require_strong=True)
