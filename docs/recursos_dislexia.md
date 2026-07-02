# Recursos de apoyo para la dislexia

Materiales y programas investigados para enriquecer el banco de actividades de CogniFit Escolar.
Los documentos físicos se guardan en `docs/pdfs/`.

---

## 1. Material de apoyo para la Dislexia
**Autora:** Profra. Juana González García (Maroleón, Gto.)  
**Fuente:** Auxiliar Didáctico "Mi Ayudante" (UPN) + Programa Integral de Estimulación de la Inteligencia "PIENSO"  
**Archivo:** `docs/pdfs/Cuadernillo de apoyo para la Dislexia.pdf.pdf`

### Tipos de ejercicios digitalizados en la app (M10_VD)
| Código | Actividad | Nivel |
|--------|-----------|-------|
| A1-A6  | Discriminación de letras especulares (b/d, p/q, n/u, b/p, d/q, m/n) | 1-2 |
| B1-B2  | Discriminación de sílabas (ba/da, de/be, pi/bi, po/bo) | 2 |
| C1-C2  | Palabras inversas especulares (sol/los, la/al, nos/son, es/se) | 3 |
| D1     | Discriminación de flechas direccionales (→/←) | 2 |

### Otros tipos de ejercicios del cuadernillo (no digitalizados aún)
- **Orientación espacial:** colorear objetos a la derecha/izquierda (págs. 2-7)
- **Discriminación de siluetas:** emparejar sombras con objetos (pág. 9-10, 28, 34)
- **Rompecabezas:** identificar piezas que completan una figura (págs. 27-28, 47)
- **Laberintos:** trazar camino de entrada a salida (págs. 16-17, 22)
- **Simetría con cuadrícula:** copiar figuras con puntos de referencia (págs. 37, 41-42)
- **Sílabas — buscar y rodear:** localizar sílaba objetivo en lista de palabras (págs. 53, 58-59)
- **Trazado de líneas enredadas:** seguir línea sin levantar el lápiz (págs. 29, 54-57)
- **Anagramas:** formar palabras con letras dadas en círculo (págs. 39-40)
- **Rotación mental:** identificar rotaciones de formas (págs. 43-44)
- **Series y patrones:** completar secuencias de figuras (pág. 48)

---

## 2. PRODISLEX — Programa de refuerzo en dislexia
**Fuente:** equipo investigador de la Universidad de Granada (España)  
**Tipo:** Programa de intervención estructurado por niveles  
**Integración actual:** ítems normalizados en `api/infrastructure/database/seeds/prodislex_items_normalizados.json`

### Áreas cubiertas
- Conciencia fonológica (segmentación, identificación de fonemas)
- Principio alfabético (grafema-fonema)
- Fluidez lectora (velocidad y precisión)
- Comprensión lectora

---

## 3. TEDE — Test Exploratorio de Dislexia Específica
**Autores:** Condemarín & Blomquist (adaptación española)  
**Tipo:** Instrumento de evaluación diagnóstica  
**Integración actual:** 102 ítems Nivel Lector (M03) + 71 ítems Errores Específicos (M05)

### Subtest 1 — Nivel Lector (M03, 102 ítems)
Nombre de letra → sonido → sílabas directas/indirectas/complejas → diptongos → fonogramas

### Subtest 2 — Errores Específicos (M05, 71 ítems)
Confundibles por sonido · Grafías semejantes · Inversiones de letras · Inversiones de palabras · Inversiones en sílaba

---

## 4. Método Orton-Gillingham
**Origen:** EE.UU. (Samuel Orton + Anna Gillingham, 1930s)  
**Enfoque:** Multisensorial, fonológico, sistemático y acumulativo  
**Relevancia:** Fundamento teórico de la mayoría de programas de intervención en dislexia  
**Componentes clave:**
- Visual-Auditivo-Kinestésico-Táctil (VAKT)
- Asociaciones grafema-fonema explícitas
- Práctica sistemática con revisión constante

*Posible ampliación:* ejercicios de dictado multisensorial para el módulo M06 (Dictado).

---

## 5. Wilson Reading System
**Origen:** EE.UU. (Barbara Wilson, 1988)  
**Enfoque:** Derivado de Orton-Gillingham, muy estructurado  
**12 pasos:** fonemas → sílabas → palabras → frases → lectura de párrafos  
**Relevancia:** El orden de progresión de dificultad en M03-M06 sigue principios similares.

---

## 6. Método Davis — Corrección de la Dislexia
**Autor:** Ronald D. Davis ("El don de la dislexia", 1994)  
**Enfoque:** Orientación perceptiva y modelado tridimensional de letras/palabras confusas  
**Relevancia para la app:**
- Los ejercicios b/d/p/q del módulo M10 están alineados con los "puntos de activación" de Davis
- La técnica de "anclar" letras problemáticas coincide con los ítems de discriminación visual

---

## 7. Reading Recovery
**Origen:** Nueva Zelanda (Marie Clay, 1976)  
**Tipo:** Intervención individualizada a corto plazo (12-20 semanas)  
**Relevancia:** El enfoque de intervención adaptativa del módulo BK-08 / recomendación  
sigue principios de Reading Recovery: nivel más alto cuando >90% aciertos, revisión cuando hay estancamiento.

---

## 8. Programa PIENSA (Estimulación Cognitiva)
**Tipo:** Fichas de estimulación cognitiva  
**Áreas:** Atención, memoria visual, razonamiento espacial, orientación  
**Vinculado con:** El cuadernillo de Profra. González García usa fichas de este programa  
**Actividades transferibles a la app:**
- Matrices de patrones (series)
- Laberintos digitales (trazado con el dedo)
- Clasificación por posición espacial

---

## Próximos módulos sugeridos

| Módulo | Contenido | Fuente |
|--------|-----------|--------|
| M11_OE | Orientación espacial (derecha/izquierda/arriba/abajo) | Cuadernillo pág. 2-7 |
| M12_SI | Siluetas y emparejamiento visual | Cuadernillo pág. 9-10 |
| M13_CF | Conciencia fonológica avanzada (fusión/segmentación) | Orton-Gillingham |
| M14_FL | Fluidez lectora con cronómetro | PRODISLEX nivel 3 |
