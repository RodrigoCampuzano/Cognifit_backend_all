# Cuadernillo de dislexia → actividades de cuadrícula (modo niño)

Fecha: 2026-07-20
Estado: aprobado (diseño), pendiente de plan de implementación

## Contexto

El "Cuadernillo de apoyo para la dislexia" (Profra. Juana González García, 65 págs.)
es un material impreso de ~60 fichas: lateralidad, discriminación visual, confusión
b/d/p/q, sílabas, laberintos, series, colorear, recortar, etc.

La app CogniFit Escolar **ya tiene** la mecánica que le va a la mayoría de las fichas
útiles: el `GridGame` del modo niño (`lib/features/child/data/child_grid_games.dart`),
una cuadrícula de 5×4 = 20 casillas donde el alumno **marca todas** las que cumplen la
consigna, se corrige al terminar (no casilla por casilla), y distingue "marcar de más"
de "dejar pasar". El puntaje es por índices (`objetivos: Set<int>`), agnóstico al
contenido de la celda.

Este trabajo lleva una parte del cuadernillo a la app como **actividades interactivas
auto-corregibles**, reusando esa mecánica.

## Decisiones tomadas (con el usuario)

1. **Forma:** actividades interactivas auto-corregibles (no réplica PDF, no solo banco).
2. **Alcance v1:** una sola mecánica — la **cuadrícula** que ya existe.
3. **Celdas:** texto **y** figuras vectoriales.
4. **Figuras:** dibujadas en la app con `CustomPainter`, mostradas espejadas/rotadas;
   se marca las que están en la **misma orientación que el modelo** (discriminación de
   orientación = raíz de la confusión b/d). Sin assets de terceros ni archivos.
5. **Ubicación:** ampliar el banco del modo niño (banco Dart local), sin backend.
6. **Selección:** catálogo de **dos niveles** (categoría → lista de juegos, con opción
   "jugar todos"). Reemplaza la corrida lineal única que hoy se reinicia al salir.

## Objetivo

- El niño abre un **catálogo**, elige una **categoría** o un **juego** concreto, y lo
  juega. Al salir/terminar vuelve al catálogo (sin reinicio de una corrida gigante).
- Se agregan ~12–16 juegos derivados del cuadernillo en 4 categorías.
- La mecánica de marcar/corregir/puntuar **no cambia**.

## No-objetivos (v1)

- Colorear, dibujar a mano alzada, recortar (requieren trazo libre).
- Laberintos / seguir con la vista, diferencias entre dibujos, series, rotación como
  copia, anagramas / formar palabras.
- Asignación por el docente y cualquier contenido servido por backend.
- Persistir qué juegos completó el niño entre sesiones (memoria de progreso).

Todo lo anterior queda como posible v2.

## Arquitectura

Todo vive en `lib/features/child/`. No hay cambios de backend ni de red.

### 1. Modelo de celda: `GridCell`

Hoy `GridGame.celdas` es `List<String>`. Se introduce un tipo sellado:

```dart
sealed class GridCell { const GridCell(); }
class TextCell extends GridCell { final String texto; const TextCell(this.texto); }
class FigureCell extends GridCell { final FigureSpec figura; const FigureCell(this.figura); }
```

`GridGame.celdas` pasa a `List<GridCell>`. El puntaje sigue siendo por índices
(`objetivos: Set<int>`), así que **no cambia**.

`FigureSpec` describe una silueta simple y su transformación:

```dart
enum FiguraForma { botita, pez, banderin }   // siluetas simples, ampliable
class FigureSpec {
  final FiguraForma forma;
  final int cuartosDeGiro;   // 0..3, giros de 90°
  final bool espejada;       // reflejo horizontal
  const FigureSpec(this.forma, {this.cuartosDeGiro = 0, this.espejada = false});
}
```

`GridGame` gana un campo opcional `FigureSpec? modelo` para mostrar la referencia
("igual que este") arriba de la cuadrícula en los juegos de orientación.

**Compatibilidad:** los helpers actuales (`_porLetra`, `gridGamesDesdeEjercicios`)
envuelven cada string en `TextCell`. El banco de texto existente sigue funcionando sin
tocar su contenido.

### 2. Categorías: `GridCategory`

`GridGame` gana `GridCategory categoria` para agrupar de forma estable en el catálogo
(en vez de agrupar por el texto de display `sectionLabel`):

```dart
enum GridCategory { buscaLetra, silabas, flechas, orientacion, cualEsDiferente }
```

Los juegos existentes se etiquetan: `kGridGames` → `buscaLetra`; los de
`gridGamesDesdeEjercicios` → `cualEsDiferente`.

### 3. Render de la cuadrícula

`_Cuadricula` (en `child_grid_game_screen.dart`) decide por celda:

- `TextCell` → el `Text` de hoy (misma tipografía serif, mismo cálculo de tamaño de
  fuente, que ahora se limita a celdas de texto).
- `FigureCell` → `CustomPaint` con `FiguraPainter`, que dibuja la silueta de
  `FigureSpec.forma` y le aplica `cuartosDeGiro` (rotación) y `espejada` (flip horizontal).

`Semantics.label` de cada casilla sale de la celda: el texto, o una descripción de la
figura (p. ej. "figura mirando a la derecha"). Los colores de corrección
(verde/rojo/naranja) y toda la lógica de aciertos/errores/omitidas **no cambian**.

Cuando `GridGame.modelo != null`, la pantalla dibuja la figura modelo (mismo
`FiguraPainter`) sobre la cuadrícula, con la etiqueta "Marca las que se ven igual que
esta".

### 4. Catálogo: `ChildGamesCatalogScreen` (nueva)

- Lista las categorías presentes en `kTodosLosGridGames` como tarjetas, en orden de
  dificultad pedagógica.
- Cada tarjeta muestra el nombre de la categoría y sus juegos (título = `question`).
- Tocar un **juego** → `ChildGridGameScreen(studentName, juegos: [ese])`.
- Botón **"Jugar todos"** por categoría → `ChildGridGameScreen(studentName, juegos:
  <subconjunto de esa categoría>)`.
- Al hacer `pop` (salir o terminar), se regresa al catálogo.

`ChildGridGameScreen` **casi no cambia**: ya acepta `List<GridGame>? juegos`. Solo se
ajusta el render de celda (punto 3). En `child_home_screen.dart`, el botón que hoy abre
`ChildGridGameScreen` pasa a abrir `ChildGamesCatalogScreen`.

## Contenido (banco nuevo)

Los **28 juegos que ya existen se conservan** (los de `kGridGames` + los de
`gridGamesDesdeEjercicios(kChildExercises)`) y quedan **categorizados** para aparecer en
el catálogo (`buscaLetra` y `cualEsDiferente`). Los del cuadernillo se **añaden encima**,
no reemplazan nada.

Nuevo archivo `lib/features/child/data/cuadernillo_grid_games.dart` con los juegos
derivados del cuadernillo, incorporados a `kTodosLosGridGames` junto a los 28 previos.
Todos cumplen los invariantes: 20 casillas, 5 columnas, con objetivos y distractores.

- **b/d/p/q en sílabas/palabras** (texto, `buscaLetra`) — pp. 4, 6, 7, 17, 20. ~3–4 juegos.
  Ej.: "Marca las sílabas que empiezan con **b**" entre celdas ba/da/pa/…
- **Busca sílabas** (texto, `silabas`) — pp. 53, 58. ~3 juegos.
  Ej.: "Marca todas las **da**" entre da/ad/ba/pa/ca.
- **Flechas / lateralidad** (glifos ←↑→↓, `flechas`) — p. 8. ~2–3 juegos.
  Ej.: "Marca todas las flechas que apuntan a la **derecha**".
- **Orientación de figuras** (figuras, `orientacion`) — pp. 15, 30, 51, 52. ~4–5 juegos.
  "Marca las que se ven igual que el modelo"; distractores = misma silueta espejada o
  girada. Objetivo = misma `forma`, mismo `cuartosDeGiro`, mismo `espejada` que el modelo.

Los índices `objetivos` se calculan a partir del contenido (como ya hace `_porLetra`),
no a mano, para no colar errores al agregar juegos.

## Manejo de errores / casos límite

- El cálculo de tamaño de fuente ignora celdas de figura (solo mira `TextCell.texto`);
  si un juego no tuviera ninguna celda de texto, se usa un tamaño por defecto.
- Un juego de orientación **debe** traer `modelo`; los de texto **no** lo llevan. Se
  cubre con test.
- Sin conexión no afecta: todo el contenido es local.

## Pruebas

- Los invariantes existentes de `child_grid_games_test.dart` (20 casillas, 5 columnas,
  objetivos+distractores, índices dentro de rango) recorren `kTodosLosGridGames` y por
  tanto cubren automáticamente los juegos nuevos.
- Nuevas:
  - Cada juego de categoría `orientacion` trae `modelo`; los demás no.
  - En un juego de orientación, `objetivos` = exactamente las celdas cuya `FigureSpec`
    coincide con el modelo (misma forma/giro/espejo); las espejadas/giradas son
    distractores.
  - Widget: una `FigureCell` renderiza un `CustomPaint` en la cuadrícula.
  - Widget: `ChildGamesCatalogScreen` agrupa por `categoria` y, al tocar un juego,
    navega a `ChildGridGameScreen` con ese único juego; "jugar todos" pasa el
    subconjunto de la categoría.
  - Smoke test de `FiguraPainter` (no lanza al pintar las 3 formas × giros/espejo).
- `flutter analyze` sin issues nuevos; suite completa en verde.

## Archivos afectados

- `lib/features/child/data/child_grid_games.dart` — `GridCell`, `FigureSpec`,
  `GridCategory`; `celdas: List<GridCell>`; `modelo`; `categoria`; helpers envuelven en
  `TextCell`; etiquetar juegos existentes.
- `lib/features/child/data/cuadernillo_grid_games.dart` — **nuevo**, banco de contenido.
- `lib/features/child/presentation/screens/child_grid_game_screen.dart` — render de
  celda texto/figura + dibujo del modelo.
- `lib/features/child/presentation/widgets/child_game_widgets.dart` — `FiguraPainter`
  (o archivo nuevo `figura_painter.dart` si conviene aislarlo).
- `lib/features/child/presentation/screens/child_games_catalog_screen.dart` — **nueva**.
- `lib/features/child/presentation/screens/child_home_screen.dart` — el botón abre el
  catálogo.
- `test/child_grid_games_test.dart` (+ tests nuevos de catálogo y painter).
