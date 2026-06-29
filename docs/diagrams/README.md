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
