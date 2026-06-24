"""
Predictor ML — carga los modelos entrenados (.pkl) y genera el perfil diagnóstico.
"""
from pathlib import Path
import joblib
import numpy as np

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


class ModelRegistry:
    """
    Carga y mantiene en memoria los modelos de subtipo y severidad.
    Se instancia una vez al arrancar la API.
    """

    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = models_dir
        self.subtype_meta = None
        self.severity_meta = None
        self.subtype_model = None
        self.severity_model = None
        self.load()

    def load(self):
        subtype_path = self.models_dir / "subtype_model_latest.pkl"
        severity_path = self.models_dir / "severity_model_latest.pkl"

        if not subtype_path.exists() or not severity_path.exists():
            raise FileNotFoundError(
                f"No se encontraron los modelos en {self.models_dir}. "
                "Ejecuta primero el notebook de entrenamiento."
            )

        self.subtype_meta = joblib.load(subtype_path)
        self.severity_meta = joblib.load(severity_path)
        self.subtype_model = self.subtype_meta["model"]
        self.severity_model = self.severity_meta["model"]

    @property
    def info(self) -> dict:
        """Metadatos de los modelos cargados (para el endpoint de versiones)."""
        return {
            "subtype": {
                "version": self.subtype_meta.get("version"),
                "metrics": self.subtype_meta.get("metrics"),
                "classes": self.subtype_meta.get("classes"),
                "dataset_sha256": self.subtype_meta.get("dataset_sha256"),
            },
            "severity": {
                "version": self.severity_meta.get("version"),
                "metrics": self.severity_meta.get("metrics"),
                "classes": self.severity_meta.get("classes"),
            },
        }


def predict_profile(feature_vector: np.ndarray, registry: ModelRegistry) -> dict:
    """
    Genera el perfil diagnóstico probabilístico a partir del feature vector.
    Idéntico a la función validada en el notebook.
    """
    fv = feature_vector.reshape(1, -1)

    subtype = registry.subtype_model.predict(fv)[0]
    subtype_proba = registry.subtype_model.predict_proba(fv)[0]
    subtype_confidence = float(max(subtype_proba))

    severity = registry.severity_model.predict(fv)[0]
    severity_proba = registry.severity_model.predict_proba(fv)[0]
    severity_confidence = float(max(severity_proba))

    clases = list(registry.subtype_model.classes_)
    if "sin_riesgo" in clases:
        idx = clases.index("sin_riesgo")
        risk = float(1 - subtype_proba[idx])
    else:
        risk = float(max(subtype_proba))

    risk_level = "bajo" if risk < 0.30 else ("medio" if risk < 0.65 else "alto")

    # Si el subtipo es sin_riesgo, la severidad no aplica
    if subtype == "sin_riesgo":
        severity = "ninguna"

    return {
        "subtype": str(subtype),
        "subtype_confidence": round(subtype_confidence, 3),
        "severity": str(severity),
        "severity_confidence": round(severity_confidence, 3),
        "risk_probability": round(risk, 3),
        "risk_level": risk_level,
        "model_version": registry.subtype_meta.get("version"),
    }
