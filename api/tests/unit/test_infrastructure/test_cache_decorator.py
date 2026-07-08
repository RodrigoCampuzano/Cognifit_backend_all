import asyncio

from infrastructure.cache.cache_decorator import cached_endpoint


def test_cached_endpoint_skips_second_call_on_hit(monkeypatch):
    """Sin Redis configurado, SemanticCache.get/set son no-op (degradan con gracia),
    así que la función decorada se ejecuta en cada llamada. Simulamos un backend en
    memoria monkeypencheando SemanticCache para verificar el comportamiento de cache-hit."""
    store: dict[str, dict] = {}

    async def fake_get(self, namespace, payload):
        return store.get(namespace)

    async def fake_set(self, namespace, payload, value, ttl=3600):
        store[namespace] = value

    from infrastructure.cache import semantic_cache

    monkeypatch.setattr(semantic_cache.SemanticCache, "get", fake_get)
    monkeypatch.setattr(semantic_cache.SemanticCache, "set", fake_set)

    call_count = 0

    @cached_endpoint("test_namespace")
    async def endpoint():
        nonlocal call_count
        call_count += 1
        return {"value": call_count}

    first = asyncio.run(endpoint())
    second = asyncio.run(endpoint())

    assert first == {"value": 1}
    assert second == {"value": 1}  # servido desde caché, no se re-ejecuta
    assert call_count == 1


def test_cached_endpoint_noop_without_redis(monkeypatch):
    """Sin Redis disponible (get_redis() devuelve None), SemanticCache.get/set son
    no-op -> la función decorada se ejecuta en cada llamada, comportamiento idéntico
    al endpoint sin decorar."""
    from infrastructure.cache import semantic_cache

    monkeypatch.setattr(semantic_cache, "get_redis", lambda: None)

    call_count = 0

    @cached_endpoint("test_namespace_no_redis")
    async def endpoint():
        nonlocal call_count
        call_count += 1
        return {"value": call_count}

    first = asyncio.run(endpoint())
    second = asyncio.run(endpoint())

    assert first == {"value": 1}
    assert second == {"value": 2}
    assert call_count == 2
