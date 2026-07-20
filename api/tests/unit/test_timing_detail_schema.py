"""`timing_detail` era el único campo del API que aceptaba cualquier JSON y lo
guardaba tal cual. Estas pruebas fijan la forma que ahora se exige."""
import pytest
from pydantic import ValidationError

from application.dtos.session_dto import TimingDetailDto


def test_acepta_el_desglose_esperado():
    d = TimingDetailDto(total_ms=8000, tts_ms=2500, background_ms=0,
                        net_ms=5500, stimulus_chars=12, stimulus_words=2,
                        difficulty=3)
    assert d.net_ms == 5500


def test_todo_es_opcional_para_no_romper_clientes_viejos():
    assert TimingDetailDto().total_ms is None


def test_rechaza_claves_desconocidas():
    """Antes se guardaban en silencio. Un campo nuevo que el servidor no
    conoce conviene descubrirlo con un 422, no meses después al entrenar."""
    with pytest.raises(ValidationError):
        TimingDetailDto(total_ms=100, campo_inventado="lo que sea")


def test_rechaza_tiempos_absurdos():
    with pytest.raises(ValidationError):
        TimingDetailDto(total_ms=-1)
    with pytest.raises(ValidationError):
        TimingDetailDto(total_ms=999_999)  # > 5 min: dato roto, no lento


def test_el_neto_no_puede_superar_al_total():
    """El neto es lo que queda tras descontar audio y segundo plano. Si lo
    supera, el cliente midió mal — y ese número pesa en el diagnóstico."""
    with pytest.raises(ValidationError) as exc:
        TimingDetailDto(total_ms=5000, net_ms=9000)
    assert "net_ms" in str(exc.value)


def test_dificultad_dentro_del_rango_del_banco():
    TimingDetailDto(difficulty=1)
    TimingDetailDto(difficulty=5)
    with pytest.raises(ValidationError):
        TimingDetailDto(difficulty=6)
