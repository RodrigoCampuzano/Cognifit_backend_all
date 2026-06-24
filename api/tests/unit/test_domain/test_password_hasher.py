from infrastructure.security.password_hasher import Argon2PasswordHasher


def test_argon2_hash_and_verify():
    hasher = Argon2PasswordHasher()
    hashed = hasher.hash("a-very-strong-password")
    assert hashed.startswith("$argon2")
    assert hasher.verify("a-very-strong-password", hashed)
    assert not hasher.verify("wrong-password", hashed)
