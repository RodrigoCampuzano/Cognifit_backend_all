from security.policies.rbac import has_role


def test_superadmin_does_not_inherit_into_clinical_roles():
    """SUPERADMIN opera la plataforma pero no debe pasar require_roles(...)
    de endpoints con datos clínicos de alumnos."""
    assert has_role("SUPERADMIN", {"SUPERADMIN"}) is True
    assert has_role("SUPERADMIN", {"ADMIN"}) is False
    assert has_role("SUPERADMIN", {"TEACHER"}) is False
    assert has_role("SUPERADMIN", {"SPECIALIST"}) is False


def test_admin_does_not_inherit_into_superadmin():
    """Un ADMIN de institución no debe poder aprobar instituciones nuevas."""
    assert has_role("ADMIN", {"SUPERADMIN"}) is False


def test_superadmin_only_role_still_valid_string():
    assert has_role("SUPERADMIN", {"SUPERADMIN", "ADMIN"}) is True
