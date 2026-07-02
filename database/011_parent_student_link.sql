-- Vincula un usuario padre/tutor a un alumno para permitir login de padres.
-- La columna user_id ya existente enlaza la cuenta propia del alumno.
-- parent_user_id enlaza la cuenta del padre/tutor para ver el perfil del hijo.

ALTER TABLE academic.students
    ADD COLUMN IF NOT EXISTS parent_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_students_parent_user ON academic.students(parent_user_id);
