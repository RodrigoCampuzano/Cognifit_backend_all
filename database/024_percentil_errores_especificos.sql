-- 024 — El segundo baremo del TEDE: Errores Específicos.
--
-- La migración 020 conectó el percentil de Nivel Lector y dejó el otro subtest
-- fuera, razonando que nuestros códigos de error (INV, SUS, OMI, ROT) no
-- corresponden a los 71 ítems fijos del TEDE.
--
-- El razonamiento era correcto y la conclusión equivocada: no había que mapear
-- códigos de error. Los 71 ítems ya estaban cargados en el banco desde el
-- principio, bajo los prefijos M05_CS, GS, IL, IP, LW y OS —doce, doce, doce,
-- once, doce y doce— que suman exactamente 71, más un ítem de práctica.
--
-- El subtest puntúa distinto al de Nivel Lector: aciertos MENOS errores. En
-- Nivel Lector el instrumento aclara que no se restan las incorrectas.

BEGIN;

ALTER TABLE diagnosis.diagnoses
    ADD COLUMN IF NOT EXISTS tede_errores_especificos JSONB;

COMMENT ON COLUMN diagnosis.diagnoses.tede_errores_especificos IS
    'Percentil normativo del subtest Errores Específicos del TEDE, por edad y '
    'por curso. Se calcula sobre los 71 ítems de los grupos M05_CS/GS/IL/IP/'
    'LW/OS con la fórmula aciertos menos errores. NULL cuando la sesión no '
    'incluyó ítems de ese subtest.';

COMMIT;

-- ─── Verificación ────────────────────────────────────────────────────────────
--
--   SELECT tede_nivel_lector->>'percentil_por_grado'        AS nivel_lector,
--          tede_errores_especificos->>'percentil_por_grado' AS errores_esp,
--          severity                                         AS severidad_modelo
--     FROM diagnosis.diagnoses ORDER BY diagnosed_at DESC;
--
-- Los dos percentiles y la severidad del modelo se leen juntos: el instrumento
-- fue diseñado para informar ambos subtests por separado.
