# Diagramas — CogniFit Backend

Fuente Mermaid (`.mmd`) + export a `.png` y `.svg` para la entrega.
Regenerar: `npx @mermaid-js/mermaid-cli -i <archivo>.mmd -o <archivo>.png -b white -s 2`
(con `PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome`).

| Diagrama | Tipo | Doc origen |
|---|---|---|
| `api_componentes` | Componentes / capas | DISENO_API.md |
| `api_clases_screening` | Clases (flujo screening/diagnóstico) | DISENO_API.md |
| `api_clases_di` | Clases (DI + seguridad) | DISENO_API.md |
| `api_despliegue` | Despliegue (Railway + Neon) | DISENO_API.md |
| `cifrado_clases` | Clases (pipeline de cifrado) | CIFRADO_DATOS_SENSIBLES.md |
| `cifrado_secuencia` | Secuencia (cifrar/descifrar) | CIFRADO_DATOS_SENSIBLES.md |
| `verificacion_gateway` | Componentes (ruta de la petición + huecos) | VERIFICACION_GATEWAY_CIFRADO_MULTITENANCY.md |
| `verificacion_cifrado` | Flujo (qué se cifra de verdad vs. código muerto) | VERIFICACION_GATEWAY_CIFRADO_MULTITENANCY.md |
| `verificacion_multitenancy` | Flujo (propagación del tenant + capas de aislamiento) | VERIFICACION_GATEWAY_CIFRADO_MULTITENANCY.md |
| `verificacion_pagos` | Secuencia (checkout tarjeta + webhook Conekta) | VERIFICACION_GATEWAY_CIFRADO_MULTITENANCY.md |
| `app_arquitectura_flutter` | Capas de la app Flutter (Clean Architecture) | APP_OVERVIEW.md · PUBLICACION_LINKEDIN.md |
| `expo_gateway_peticion` | Secuencia (petición de punta a punta + cortes 401/403/429) | expo_arquitectura_critica/01_api_gateway.md |
| `expo_pago_fallido` | Secuencia (4 modos de falla de una transacción) | expo_arquitectura_critica/02_sistema_pagos.md |
| `expo_cifrado_flujo_datos` | Flujo de datos (dónde se cifra: tránsito y reposo) | expo_arquitectura_critica/03_cifrado_seguridad.md |
| `expo_gestion_claves` | Flujo (ciclo de vida de secretos + rotación) | expo_arquitectura_critica/03_cifrado_seguridad.md |

> Los cuatro `verificacion_*` documentan el **estado real verificado en código**, no el
> diseño deseado: en verde lo implementado, en rojo los huecos detectados.
> Los cuatro `expo_*` son el material de exposición derivado de esa verificación
> (ver [`../expo_arquitectura_critica/`](../expo_arquitectura_critica/)).
