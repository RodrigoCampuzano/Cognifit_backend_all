# Cuadernillo de dislexia → cuadrículas del modo niño — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ampliar el banco de cuadrículas del modo niño con actividades del cuadernillo de dislexia (texto y figuras vectoriales), y reemplazar la corrida lineal por un catálogo de dos niveles donde el niño elige categoría o juego.

**Architecture:** Se introduce un tipo de celda `GridCell` (texto o figura) y se conserva intacta la mecánica de marcar/corregir/puntuar (por índices). Las figuras se dibujan con `CustomPainter` mostradas espejadas/rotadas. Los 28 juegos existentes se conservan, se categorizan y se suman los del cuadernillo; un catálogo nuevo agrupa todo por categoría.

**Tech Stack:** Flutter/Dart, `CustomPainter`, `flutter_test`. Sin backend, sin dependencias nuevas.

## Global Constraints

- Trabajar solo en `lib/features/child/` y `test/`. NO tocar backend ni red.
- `flutter analyze`: 0 errores/warnings nuevos. Usar `.withValues(alpha:)`, no `.withOpacity`.
- `flutter test`: suite completa en verde al final de cada tarea que toque pantallas.
- Todos los `GridGame` cumplen los invariantes ya fijados por `test/child_grid_games_test.dart`: exactamente **20 casillas**, **5 columnas**, con objetivos y también distractores, e índices objetivo dentro de rango.
- Commits GPG-firmados (Verified), SIN trailer `Co-Authored-By`.
- Rama de trabajo: `feat/cuadernillo-cuadriculas` (ya creada).

---

### Task 1: Tipos base — `GridCell`, `FigureSpec`, `GridCategory`

Introduce los tipos nuevos de forma **aditiva** (aún no se cambia `GridGame`), para que el archivo siga compilando.

**Files:**
- Modify: `lib/features/child/data/child_grid_games.dart` (agregar tipos cerca del inicio, después de los imports)
- Test: `test/grid_cell_test.dart`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `enum FiguraForma { botita, pez, banderin }`
  - `class FigureSpec { final FiguraForma forma; final int cuartosDeGiro; final bool espejada; const FigureSpec(this.forma, {this.cuartosDeGiro = 0, this.espejada = false}); }` con `operator ==` y `hashCode` por valor.
  - `sealed class GridCell { const GridCell(); String get semanticLabel; }`
  - `class TextCell extends GridCell { final String texto; const TextCell(this.texto); }`
  - `class FigureCell extends GridCell { final FigureSpec figura; const FigureCell(this.figura); }`
  - `enum GridCategory { buscaLetra, silabas, flechas, orientacion, cualEsDiferente }`

- [ ] **Step 1: Write the failing test**

Crear `test/grid_cell_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:cognifit_mobile/features/child/data/child_grid_games.dart';

void main() {
  test('FigureSpec compara por valor (forma, giro, espejo)', () {
    const a = FigureSpec(FiguraForma.pez, cuartosDeGiro: 1, espejada: true);
    const b = FigureSpec(FiguraForma.pez, cuartosDeGiro: 1, espejada: true);
    const c = FigureSpec(FiguraForma.pez, cuartosDeGiro: 1, espejada: false);
    expect(a, equals(b));
    expect(a, isNot(equals(c)));
    expect(a.hashCode, equals(b.hashCode));
  });

  test('TextCell expone su texto como etiqueta accesible', () {
    const celda = TextCell('b');
    expect(celda.semanticLabel, 'b');
  });

  test('FigureCell describe su orientación en la etiqueta accesible', () {
    const celda = FigureCell(FigureSpec(FiguraForma.pez, espejada: true));
    expect(celda.semanticLabel, contains('pez'));
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/grid_cell_test.dart`
Expected: FAIL de compilación — `FigureSpec`, `TextCell`, etc. no existen.

- [ ] **Step 3: Add the types**

En `lib/features/child/data/child_grid_games.dart`, justo después de `import 'child_exercises.dart';`, agregar:

```dart
/// Categorías con las que el catálogo agrupa los juegos. Es un valor estable,
/// distinto del `sectionLabel` de display (que puede repetirse o cambiar).
enum GridCategory { buscaLetra, silabas, flechas, orientacion, cualEsDiferente }

/// Silueta simple y asimétrica: al espejarla o girarla se nota, que es lo que
/// hace falta para discriminar orientación (la raíz de la confusión b/d).
enum FiguraForma { botita, pez, banderin }

/// Una figura y su orientación. Se compara por valor para poder decidir qué
/// casillas "se ven igual que el modelo" sin listar índices a mano.
class FigureSpec {
  final FiguraForma forma;
  final int cuartosDeGiro; // 0..3, giros de 90°
  final bool espejada; // reflejo horizontal
  const FigureSpec(this.forma, {this.cuartosDeGiro = 0, this.espejada = false});

  @override
  bool operator ==(Object other) =>
      other is FigureSpec &&
      other.forma == forma &&
      other.cuartosDeGiro == cuartosDeGiro &&
      other.espejada == espejada;

  @override
  int get hashCode => Object.hash(forma, cuartosDeGiro, espejada);
}

/// Una casilla de la cuadrícula: o una letra/sílaba/glifo, o una figura.
sealed class GridCell {
  const GridCell();

  /// Etiqueta para lectores de pantalla.
  String get semanticLabel;
}

class TextCell extends GridCell {
  final String texto;
  const TextCell(this.texto);

  @override
  String get semanticLabel => texto;
}

class FigureCell extends GridCell {
  final FigureSpec figura;
  const FigureCell(this.figura);

  @override
  String get semanticLabel {
    final giro = figura.cuartosDeGiro == 0 ? '' : ' girada';
    final espejo = figura.espejada ? ' espejada' : '';
    return 'figura ${figura.forma.name}$giro$espejo';
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/grid_cell_test.dart`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/features/child/data/child_grid_games.dart test/grid_cell_test.dart
git commit -m "feat(niño): tipos de celda (texto/figura), FigureSpec y categorías"
```

---

### Task 2: Migrar `GridGame` a `List<GridCell>` + categoría + modelo

Cambio atómico de tipo: `GridGame.celdas` pasa de `List<String>` a `List<GridCell>`, gana `categoria` y `modelo?`. Se actualizan los dos helpers y el render de texto de la pantalla para que compile y la suite quede verde. El contenido de los juegos existentes NO cambia (solo se envuelve en `TextCell` y se etiqueta la categoría).

**Files:**
- Modify: `lib/features/child/data/child_grid_games.dart` (clase `GridGame`, `gridGamesDesdeEjercicios`, `_porLetra`)
- Modify: `lib/features/child/presentation/screens/child_grid_game_screen.dart` (`_Cuadricula`: cálculo de fuente y render de texto; `Semantics.label`)
- Test: `test/child_grid_games_test.dart` (agregar aserciones de categoría)

**Interfaces:**
- Consumes: `GridCell`, `TextCell`, `FigureSpec`, `GridCategory` (Task 1).
- Produces:
  - `GridGame` con `final List<GridCell> celdas; final GridCategory categoria; final FigureSpec? modelo;`
  - `_porLetra(...)` gana parámetro `required GridCategory categoria` y produce `TextCell`.
  - `gridGamesDesdeEjercicios` produce `TextCell` y `categoria: GridCategory.cualEsDiferente`.

- [ ] **Step 1: Write the failing test**

En `test/child_grid_games_test.dart`, dentro de `group('banco de cuadrículas', ...)`, agregar:

```dart
    test('todos los juegos previos son de celdas de texto y tienen categoría', () {
      for (final j in kTodosLosGridGames) {
        for (final c in j.celdas) {
          expect(c, isA<TextCell>(), reason: '${j.id} tiene una celda no-texto');
        }
      }
      // Las categorías previas: letra (banco a mano) y "cuál es diferente".
      final cats = kTodosLosGridGames.map((j) => j.categoria).toSet();
      expect(cats, contains(GridCategory.buscaLetra));
      expect(cats, contains(GridCategory.cualEsDiferente));
    });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/child_grid_games_test.dart`
Expected: FAIL de compilación — `GridGame` aún usa `List<String>`, no existe `categoria`.

- [ ] **Step 3: Migrar la clase `GridGame`**

En `lib/features/child/data/child_grid_games.dart`, reemplazar la declaración de campos y el constructor de `GridGame` por:

```dart
  final String id;
  final String sectionLabel;
  final String question;
  final String instruction;

  /// Las 20 casillas, en el orden en que se muestran.
  final List<GridCell> celdas;

  /// Cuáles hay que tocar. El resto son distractores.
  final Set<int> objetivos;

  /// Qué se explica al terminar, sea que acertó o no.
  final String explanation;

  /// Categoría estable para agrupar en el catálogo.
  final GridCategory categoria;

  /// Figura de referencia para los juegos de orientación ("igual que esta").
  /// Nula en los juegos de texto.
  final FigureSpec? modelo;

  final int columnas;
  final int difficulty;

  const GridGame({
    required this.id,
    required this.sectionLabel,
    required this.question,
    required this.instruction,
    required this.celdas,
    required this.objetivos,
    required this.explanation,
    required this.categoria,
    this.modelo,
    this.columnas = 5,
    this.difficulty = 1,
  });

  int get totalObjetivos => objetivos.length;
```

- [ ] **Step 4: Actualizar los helpers**

En la misma archivo, en `gridGamesDesdeEjercicios`, reemplazar la construcción de `celdas` y el `return GridGame(...)` por:

```dart
    final celdas = List<GridCell>.filled(20, TextCell(e.mainOption));
    celdas[pos] = TextCell(e.oddOption);
    return GridGame(
      id: 'GRID_${e.id}',
      sectionLabel: e.sectionLabel,
      question: e.question,
      instruction: 'Toca la que es diferente. Están entre otras 19.',
      celdas: celdas,
      objetivos: {pos},
      explanation: e.explanation,
      categoria: GridCategory.cualEsDiferente,
      difficulty: e.difficulty,
    );
```

En `_porLetra`, cambiar la firma para recibir `categoria` y envolver en `TextCell`. Reemplazar la función completa por:

```dart
GridGame _porLetra({
  required String id,
  required String sectionLabel,
  required String question,
  required String instruction,
  required List<String> celdas,
  required String objetivo,
  required String explanation,
  required GridCategory categoria,
  int difficulty = 1,
}) {
  final objetivos = <int>{};
  for (var i = 0; i < celdas.length; i++) {
    if (celdas[i] == objetivo) objetivos.add(i);
  }
  return GridGame(
    id: id,
    sectionLabel: sectionLabel,
    question: question,
    instruction: instruction,
    celdas: [for (final c in celdas) TextCell(c)],
    objetivos: objetivos,
    explanation: explanation,
    categoria: categoria,
    difficulty: difficulty,
  );
}
```

- [ ] **Step 5: Etiquetar los juegos de `kGridGames`**

Cada llamada a `_porLetra(...)` dentro de `final List<GridGame> kGridGames = [ ... ]` debe pasar `categoria: GridCategory.buscaLetra,`. Agregar esa línea (por ejemplo, junto a `objetivo:`) en **todas** las entradas de `kGridGames`.

- [ ] **Step 6: Actualizar el render de texto en la pantalla**

En `lib/features/child/presentation/screens/child_grid_game_screen.dart`, dentro de `_Cuadricula.build`, reemplazar el cálculo de fuente por uno que solo mire las celdas de texto:

```dart
    // Solo las celdas de texto influyen en el tamaño de fuente; las figuras se
    // pintan aparte. Si no hubiera texto, se usa un tamaño por defecto.
    final largos = juego.celdas.whereType<TextCell>().map((c) => c.texto.length);
    final maxLargo = largos.isEmpty ? 1 : largos.reduce((a, b) => a > b ? a : b);
    final fuente = maxLargo <= 1 ? 34.0 : (maxLargo <= 3 ? 22.0 : 16.0);
```

En el `itemBuilder`, reemplazar el `Semantics(... label: juego.celdas[i], ...)` por `label: juego.celdas[i].semanticLabel,`.

Reemplazar el contenido central de la casilla (el `Center(child: Padding(... Text(juego.celdas[i] ...)))`) por un `switch` sobre el tipo de celda:

```dart
                Center(
                  child: Padding(
                    padding: const EdgeInsets.all(2),
                    child: switch (juego.celdas[i]) {
                      TextCell(:final texto) => FittedBox(
                          child: Text(texto,
                              style: TextStyle(
                                fontSize: fuente,
                                fontWeight: FontWeight.w700,
                                fontFamily: 'serif',
                                color: AppTheme.onSurface,
                              )),
                        ),
                      // El caso de figura se implementa en la Task 3; por ahora
                      // se deja un hueco que no se usa (no hay juegos de figura
                      // todavía).
                      FigureCell() => const SizedBox.shrink(),
                    },
                  ),
                ),
```

- [ ] **Step 7: Run the full suite**

Run: `flutter test`
Expected: PASS — incluidos los invariantes previos y la aserción nueva de categorías.

Run: `flutter analyze`
Expected: 0 nuevos.

- [ ] **Step 8: Commit**

```bash
git add lib/features/child/data/child_grid_games.dart \
        lib/features/child/presentation/screens/child_grid_game_screen.dart \
        test/child_grid_games_test.dart
git commit -m "refactor(niño): celdas GridCell y categoría en GridGame (contenido intacto)"
```

---

### Task 3: `FiguraPainter` y render de celdas de figura

Dibuja las siluetas y las muestra en las casillas de figura y como modelo arriba de la cuadrícula.

**Files:**
- Create: `lib/features/child/presentation/widgets/figura_painter.dart`
- Modify: `lib/features/child/presentation/screens/child_grid_game_screen.dart` (render de `FigureCell`; dibujar `modelo`)
- Test: `test/figura_painter_test.dart`

**Interfaces:**
- Consumes: `FigureSpec`, `FiguraForma` (Task 1); `GridGame.modelo`, `FigureCell` (Task 2).
- Produces:
  - `class FiguraView extends StatelessWidget { final FigureSpec figura; final Color color; const FiguraView({super.key, required this.figura, this.color}); }` — envuelve un `CustomPaint` con `FiguraPainter`.
  - `class FiguraPainter extends CustomPainter` (usada por `FiguraView`).

- [ ] **Step 1: Write the failing test**

Crear `test/figura_painter_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:cognifit_mobile/features/child/data/child_grid_games.dart';
import 'package:cognifit_mobile/features/child/presentation/widgets/figura_painter.dart';

void main() {
  testWidgets('FiguraView pinta cualquier forma/orientación sin lanzar', (t) async {
    for (final forma in FiguraForma.values) {
      for (final espejada in [false, true]) {
        for (var giro = 0; giro < 4; giro++) {
          await t.pumpWidget(MaterialApp(
            home: Scaffold(
              body: Center(
                child: SizedBox(
                  width: 60,
                  height: 60,
                  child: FiguraView(
                    figura: FigureSpec(forma, cuartosDeGiro: giro, espejada: espejada),
                  ),
                ),
              ),
            ),
          ));
          expect(find.byType(CustomPaint), findsWidgets);
        }
      }
    }
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/figura_painter_test.dart`
Expected: FAIL de compilación — `FiguraView`/`figura_painter.dart` no existen.

- [ ] **Step 3: Implementar el painter**

Crear `lib/features/child/presentation/widgets/figura_painter.dart`:

```dart
import 'dart:math';

import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../data/child_grid_games.dart';

/// Muestra una [FigureSpec] como silueta rellena, aplicándole el giro y el
/// espejo. Las siluetas son asimétricas a propósito: así el espejo o el giro
/// se notan y hay algo que discriminar.
class FiguraView extends StatelessWidget {
  final FigureSpec figura;
  final Color? color;
  const FiguraView({super.key, required this.figura, this.color});

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: FiguraPainter(figura, color ?? AppTheme.onSurface),
    );
  }
}

class FiguraPainter extends CustomPainter {
  final FigureSpec figura;
  final Color color;
  FiguraPainter(this.figura, this.color);

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.translate(size.width / 2, size.height / 2);
    if (figura.espejada) canvas.scale(-1, 1);
    canvas.rotate(figura.cuartosDeGiro * pi / 2);
    canvas.translate(-size.width / 2, -size.height / 2);

    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;
    canvas.drawPath(_path(figura.forma, size), paint);
    canvas.restore();
  }

  /// Todas las formas se definen en coordenadas relativas (0..1) y se escalan
  /// al tamaño de la casilla.
  Path _path(FiguraForma forma, Size s) {
    final w = s.width, h = s.height;
    Offset p(double x, double y) => Offset(x * w, y * h);
    final path = Path();
    switch (forma) {
      case FiguraForma.pez:
        // Pez con la nariz a la derecha y la cola bífida a la izquierda.
        path.moveTo(p(0.90, 0.50).dx, p(0.90, 0.50).dy);
        path.lineTo(p(0.45, 0.22).dx, p(0.45, 0.22).dy);
        path.lineTo(p(0.18, 0.34).dx, p(0.18, 0.34).dy);
        path.lineTo(p(0.32, 0.50).dx, p(0.32, 0.50).dy);
        path.lineTo(p(0.18, 0.66).dx, p(0.18, 0.66).dy);
        path.lineTo(p(0.45, 0.78).dx, p(0.45, 0.78).dy);
        path.close();
      case FiguraForma.banderin:
        // Asta vertical a la izquierda y banderín triangular a la derecha.
        path.addRect(Rect.fromLTRB(p(0.18, 0.10).dx, p(0.18, 0.10).dy,
            p(0.24, 0.90).dx, p(0.24, 0.90).dy));
        path.moveTo(p(0.24, 0.12).dx, p(0.24, 0.12).dy);
        path.lineTo(p(0.82, 0.26).dx, p(0.82, 0.26).dy);
        path.lineTo(p(0.24, 0.40).dx, p(0.24, 0.40).dy);
        path.close();
      case FiguraForma.botita:
        // Bota con la punta a la derecha.
        path.moveTo(p(0.36, 0.15).dx, p(0.36, 0.15).dy);
        path.lineTo(p(0.56, 0.15).dx, p(0.56, 0.15).dy);
        path.lineTo(p(0.56, 0.58).dx, p(0.56, 0.58).dy);
        path.lineTo(p(0.82, 0.58).dx, p(0.82, 0.58).dy);
        path.lineTo(p(0.82, 0.82).dx, p(0.82, 0.82).dy);
        path.lineTo(p(0.36, 0.82).dx, p(0.36, 0.82).dy);
        path.close();
    }
    return path;
  }

  @override
  bool shouldRepaint(FiguraPainter old) =>
      old.figura != figura || old.color != color;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/figura_painter_test.dart`
Expected: PASS.

- [ ] **Step 5: Renderizar la figura en la casilla y el modelo**

En `lib/features/child/presentation/screens/child_grid_game_screen.dart`, agregar el import:

```dart
import '../widgets/figura_painter.dart';
```

Reemplazar el caso `FigureCell() => const SizedBox.shrink(),` del `switch` (de la Task 2) por:

```dart
                      FigureCell(:final figura) => Padding(
                          padding: const EdgeInsets.all(8),
                          child: FiguraView(figura: figura),
                        ),
```

En el `Column` de la pantalla (`_ChildGridGameScreenState.build`), justo **antes** del widget `_Cuadricula(...)`, insertar el modelo cuando exista:

```dart
                if (_juego.modelo != null) ...[
                  Row(children: [
                    Container(
                      width: 54,
                      height: 54,
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.primary, width: 2),
                      ),
                      child: FiguraView(figura: _juego.modelo!, color: AppTheme.primary),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text('Marca las que se ven igual que esta.',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: const Color(0xFF6B6880))),
                    ),
                  ]),
                  const SizedBox(height: 14),
                ],
```

- [ ] **Step 6: Run the full suite**

Run: `flutter test`
Expected: PASS.

Run: `flutter analyze`
Expected: 0 nuevos.

- [ ] **Step 7: Commit**

```bash
git add lib/features/child/presentation/widgets/figura_painter.dart \
        lib/features/child/presentation/screens/child_grid_game_screen.dart \
        test/figura_painter_test.dart
git commit -m "feat(niño): dibujo de figuras vectoriales en casillas y modelo"
```

---

### Task 4: Helper y banco de juegos de orientación (figuras)

**Files:**
- Create: `lib/features/child/data/cuadernillo_grid_games.dart`
- Modify: `lib/features/child/data/child_grid_games.dart` (`kTodosLosGridGames` incluye el banco nuevo)
- Test: `test/cuadernillo_grid_games_test.dart`

**Interfaces:**
- Consumes: `GridGame`, `GridCell`, `FigureCell`, `FigureSpec`, `FiguraForma`, `GridCategory` (Tasks 1-2).
- Produces:
  - `List<GridGame> kJuegosOrientacion` — juegos de categoría `orientacion`, cada uno con `modelo` y celdas `FigureCell`.
  - (En este task) `List<GridGame> get kCuadernilloGridGames => [...kJuegosOrientacion];` (se ampliará en Task 5).

- [ ] **Step 1: Write the failing test**

Crear `test/cuadernillo_grid_games_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:cognifit_mobile/features/child/data/child_grid_games.dart';
import 'package:cognifit_mobile/features/child/data/cuadernillo_grid_games.dart';

void main() {
  group('juegos de orientación', () {
    test('cada juego de orientación trae modelo y solo celdas de figura', () {
      for (final j in kJuegosOrientacion) {
        expect(j.categoria, GridCategory.orientacion, reason: j.id);
        expect(j.modelo, isNotNull, reason: '${j.id} no tiene modelo');
        for (final c in j.celdas) {
          expect(c, isA<FigureCell>(), reason: '${j.id} tiene celda no-figura');
        }
      }
    });

    test('los objetivos son exactamente las figuras iguales al modelo', () {
      for (final j in kJuegosOrientacion) {
        final iguales = <int>{};
        for (var i = 0; i < j.celdas.length; i++) {
          final c = j.celdas[i] as FigureCell;
          if (c.figura == j.modelo) iguales.add(i);
        }
        expect(j.objetivos, equals(iguales),
            reason: '${j.id}: objetivos no coinciden con las iguales al modelo');
      }
    });

    test('hay distractores espejados o girados (no todo es igual al modelo)', () {
      for (final j in kJuegosOrientacion) {
        expect(j.objetivos.length, lessThan(20), reason: '${j.id} no discrimina nada');
      }
    });

    test('los juegos de orientación están en kTodosLosGridGames', () {
      final ids = kTodosLosGridGames.map((j) => j.id).toSet();
      for (final j in kJuegosOrientacion) {
        expect(ids, contains(j.id));
      }
    });
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/cuadernillo_grid_games_test.dart`
Expected: FAIL de compilación — `cuadernillo_grid_games.dart` no existe.

- [ ] **Step 3: Implementar el helper y el banco de orientación**

Crear `lib/features/child/data/cuadernillo_grid_games.dart`:

```dart
/// Banco de cuadrículas derivado del "Cuadernillo de apoyo para la dislexia".
///
/// Se suma a los juegos que ya existían (banco de letras + "cuál es diferente"),
/// no los reemplaza. Acá viven las categorías nuevas: orientación (figuras),
/// sílabas y flechas. Las de letras se quedan en child_grid_games.dart.
library;

import 'child_grid_games.dart';

/// Construye un juego de orientación: marca como objetivo cada casilla cuya
/// figura sea igual al [modelo] (misma forma, giro y espejo). Evita listar
/// índices a mano.
GridGame _porOrientacion({
  required String id,
  required String question,
  required FigureSpec modelo,
  required List<FigureSpec> figuras,
  required String explanation,
  int difficulty = 1,
}) {
  assert(figuras.length == 20, '$id debe tener 20 figuras');
  final objetivos = <int>{};
  for (var i = 0; i < figuras.length; i++) {
    if (figuras[i] == modelo) objetivos.add(i);
  }
  return GridGame(
    id: id,
    sectionLabel: 'MISMA ORIENTACIÓN',
    question: question,
    instruction: 'Toca todas las que están igual que el modelo. '
        'Las volteadas o giradas no cuentan.',
    celdas: [for (final f in figuras) FigureCell(f)],
    objetivos: objetivos,
    explanation: explanation,
    categoria: GridCategory.orientacion,
    modelo: modelo,
    difficulty: difficulty,
  );
}

/// Atajos para no repetir `FigureSpec(...)` en cada casilla.
FigureSpec _f(FiguraForma forma, {int giro = 0, bool esp = false}) =>
    FigureSpec(forma, cuartosDeGiro: giro, espejada: esp);

final List<GridGame> kJuegosOrientacion = [
  // 1) Pez mirando a la derecha vs. pez espejado (mira a la izquierda).
  //    Es el caso más parecido a b/d: misma figura, solo cambia el lado.
  _porOrientacion(
    id: 'ORI_pez_espejo',
    question: 'Peces que miran igual',
    modelo: _f(FiguraForma.pez),
    figuras: [
      _f(FiguraForma.pez), _f(FiguraForma.pez, esp: true), _f(FiguraForma.pez),
      _f(FiguraForma.pez, esp: true), _f(FiguraForma.pez),
      _f(FiguraForma.pez, esp: true), _f(FiguraForma.pez), _f(FiguraForma.pez, esp: true),
      _f(FiguraForma.pez), _f(FiguraForma.pez, esp: true),
      _f(FiguraForma.pez), _f(FiguraForma.pez), _f(FiguraForma.pez, esp: true),
      _f(FiguraForma.pez, esp: true), _f(FiguraForma.pez),
      _f(FiguraForma.pez, esp: true), _f(FiguraForma.pez), _f(FiguraForma.pez, esp: true),
      _f(FiguraForma.pez), _f(FiguraForma.pez, esp: true),
    ],
    explanation:
        'El pez del modelo mira a la derecha. El espejado mira al otro lado, '
        'igual que la b y la d: son la misma forma volteada.',
  ),

  // 2) Botita en su posición vs. girada.
  _porOrientacion(
    id: 'ORI_botita_giro',
    question: 'Botas paradas igual',
    modelo: _f(FiguraForma.botita),
    figuras: [
      _f(FiguraForma.botita), _f(FiguraForma.botita, giro: 1), _f(FiguraForma.botita),
      _f(FiguraForma.botita, giro: 2), _f(FiguraForma.botita),
      _f(FiguraForma.botita, giro: 1), _f(FiguraForma.botita), _f(FiguraForma.botita, giro: 3),
      _f(FiguraForma.botita), _f(FiguraForma.botita, giro: 2),
      _f(FiguraForma.botita), _f(FiguraForma.botita, giro: 1), _f(FiguraForma.botita),
      _f(FiguraForma.botita, giro: 3), _f(FiguraForma.botita, giro: 2),
      _f(FiguraForma.botita), _f(FiguraForma.botita, giro: 1), _f(FiguraForma.botita),
      _f(FiguraForma.botita, giro: 2), _f(FiguraForma.botita, giro: 3),
    ],
    explanation:
        'Girar una figura cambia hacia dónde apunta. Solo las que están paradas '
        'igual que el modelo cuentan.',
    difficulty: 2,
  ),

  // 3) Banderín igual vs. espejado y girado (mezcla, más difícil).
  _porOrientacion(
    id: 'ORI_banderin_mix',
    question: 'Banderines iguales',
    modelo: _f(FiguraForma.banderin),
    figuras: [
      _f(FiguraForma.banderin), _f(FiguraForma.banderin, esp: true), _f(FiguraForma.banderin, giro: 2),
      _f(FiguraForma.banderin), _f(FiguraForma.banderin, giro: 1),
      _f(FiguraForma.banderin, esp: true), _f(FiguraForma.banderin), _f(FiguraForma.banderin, giro: 3),
      _f(FiguraForma.banderin, esp: true), _f(FiguraForma.banderin),
      _f(FiguraForma.banderin, giro: 2), _f(FiguraForma.banderin), _f(FiguraForma.banderin, esp: true),
      _f(FiguraForma.banderin, giro: 1), _f(FiguraForma.banderin),
      _f(FiguraForma.banderin, esp: true), _f(FiguraForma.banderin, giro: 2), _f(FiguraForma.banderin),
      _f(FiguraForma.banderin, giro: 3), _f(FiguraForma.banderin, esp: true),
    ],
    explanation:
        'Aquí hay banderines volteados y girados. Solo el que está exactamente '
        'igual que el modelo cuenta.',
    difficulty: 3,
  ),

  // 4) Pez del modelo entre peces espejados Y botitas (otra forma). Una forma
  //    distinta nunca es "igual al modelo": ayuda a separar "qué figura es" de
  //    "cómo está orientada".
  _porOrientacion(
    id: 'ORI_pez_entre_botas',
    question: 'Solo los peces que miran igual',
    modelo: _f(FiguraForma.pez),
    figuras: [
      _f(FiguraForma.pez), _f(FiguraForma.botita), _f(FiguraForma.pez, esp: true),
      _f(FiguraForma.pez), _f(FiguraForma.botita, giro: 1),
      _f(FiguraForma.pez, esp: true), _f(FiguraForma.pez), _f(FiguraForma.botita),
      _f(FiguraForma.pez), _f(FiguraForma.pez, esp: true),
      _f(FiguraForma.botita, giro: 2), _f(FiguraForma.pez), _f(FiguraForma.pez, esp: true),
      _f(FiguraForma.pez), _f(FiguraForma.botita),
      _f(FiguraForma.pez, esp: true), _f(FiguraForma.pez), _f(FiguraForma.botita, giro: 3),
      _f(FiguraForma.pez, esp: true), _f(FiguraForma.pez),
    ],
    explanation:
        'Las botas no son peces: nunca cuentan. De los peces, solo los que '
        'miran igual que el modelo.',
    difficulty: 3,
  ),
];

/// Todo el contenido nuevo del cuadernillo. Se amplía en la Task 5.
List<GridGame> get kCuadernilloGridGames => [
      ...kJuegosOrientacion,
    ];
```

- [ ] **Step 4: Incluir el banco nuevo en `kTodosLosGridGames`**

En `lib/features/child/data/child_grid_games.dart`, agregar el import al inicio (junto a `import 'child_exercises.dart';`):

```dart
import 'cuadernillo_grid_games.dart';
```

Y reemplazar el getter `kTodosLosGridGames` por:

```dart
List<GridGame> get kTodosLosGridGames => [
      ...kGridGames,
      ...gridGamesDesdeEjercicios(kChildExercises),
      ...kCuadernilloGridGames,
    ];
```

- [ ] **Step 5: Run the tests**

Run: `flutter test test/cuadernillo_grid_games_test.dart test/child_grid_games_test.dart`
Expected: PASS — incluidos los invariantes previos (20 casillas / 5 columnas / objetivos+distractores) aplicados ahora también a los juegos de orientación.

- [ ] **Step 6: Commit**

```bash
git add lib/features/child/data/cuadernillo_grid_games.dart \
        lib/features/child/data/child_grid_games.dart \
        test/cuadernillo_grid_games_test.dart
git commit -m "feat(niño): juegos de orientación de figuras (cuadernillo)"
```

---

### Task 5: Bancos de texto del cuadernillo — sílabas y flechas

**Files:**
- Modify: `lib/features/child/data/cuadernillo_grid_games.dart` (agregar bancos de sílabas y flechas; ampliar `kCuadernilloGridGames`)
- Modify: `lib/features/child/data/child_grid_games.dart` (exportar/reusar `_porLetra`; ver nota)
- Test: `test/cuadernillo_grid_games_test.dart` (aserciones de categorías nuevas)

**Nota sobre `_porLetra`:** hoy es privada de `child_grid_games.dart`. Para reusarla desde `cuadernillo_grid_games.dart`, renombrarla a **pública** `porTextoObjetivo` (mismo cuerpo y firma que quedó en Task 2, solo sin el guion bajo) y actualizar sus llamadas en `kGridGames`. Así el banco de sílabas/flechas usa el mismo constructor probado en vez de duplicarlo.

**Interfaces:**
- Consumes: `porTextoObjetivo(...)` (renombrada), `GridCategory` (Tasks 1-2).
- Produces:
  - `List<GridGame> kJuegosSilabas`, `List<GridGame> kJuegosFlechas` (categorías `silabas` y `flechas`).
  - `kCuadernilloGridGames` amplía para incluirlos.

- [ ] **Step 1: Write the failing test**

En `test/cuadernillo_grid_games_test.dart`, agregar al final de `main()`:

```dart
  group('juegos de texto del cuadernillo', () {
    test('están presentes las categorías sílabas y flechas', () {
      final cats = kCuadernilloGridGames.map((j) => j.categoria).toSet();
      expect(cats, contains(GridCategory.silabas));
      expect(cats, contains(GridCategory.flechas));
    });

    test('los juegos de flechas usan glifos de dirección', () {
      final flechas = kCuadernilloGridGames
          .where((j) => j.categoria == GridCategory.flechas);
      expect(flechas, isNotEmpty);
      for (final j in flechas) {
        for (final c in j.celdas) {
          expect(c, isA<TextCell>());
          expect('←↑→↓', contains((c as TextCell).texto));
        }
      }
    });
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/cuadernillo_grid_games_test.dart`
Expected: FAIL — `kJuegosSilabas`/`kJuegosFlechas` no existen; categorías ausentes.

- [ ] **Step 3: Hacer pública `porTextoObjetivo`**

En `lib/features/child/data/child_grid_games.dart`, renombrar `_porLetra` a `porTextoObjetivo` (quitar el guion bajo del nombre en la definición) y actualizar **todas** sus llamadas dentro de `kGridGames` (buscar `_porLetra(` → `porTextoObjetivo(`).

- [ ] **Step 4: Agregar los bancos de sílabas y flechas**

En `lib/features/child/data/cuadernillo_grid_games.dart`, agregar antes del getter `kCuadernilloGridGames`:

```dart
/// Sílabas: se marca todas las iguales a la buscada, entre parecidas (da/ad,
/// ba/ab, pa/ap…). Es la ficha "busca sílabas" del cuadernillo (pp. 53, 58).
final List<GridGame> kJuegosSilabas = [
  porTextoObjetivo(
    id: 'SIL_da',
    sectionLabel: 'BUSCA LA SÍLABA',
    question: 'Encuentra todas las «da»',
    instruction: 'Toca cada «da». Cuidado con «ad», que lleva las mismas letras.',
    celdas: const [
      'da', 'ad', 'ba', 'da', 'ad',
      'da', 'ba', 'ad', 'da', 'da',
      'ad', 'da', 'ba', 'ad', 'da',
      'da', 'ad', 'da', 'ba', 'ad',
    ],
    objetivo: 'da',
    explanation:
        '«da» empieza con la d y termina con la a. «ad» tiene las mismas letras '
        'al revés: fíjate por cuál empieza.',
    categoria: GridCategory.silabas,
  ),
  porTextoObjetivo(
    id: 'SIL_ba',
    sectionLabel: 'BUSCA LA SÍLABA',
    question: 'Encuentra todas las «ba»',
    instruction: 'Toca cada «ba». La «ab» y la «pa» se le parecen.',
    celdas: const [
      'ba', 'ab', 'pa', 'ba', 'ab',
      'ba', 'pa', 'ba', 'ab', 'ba',
      'pa', 'ab', 'ba', 'ba', 'ab',
      'ba', 'pa', 'ab', 'ba', 'pa',
    ],
    objetivo: 'ba',
    explanation:
        '«ba» empieza con la b. «pa» empieza con la p (mira hacia abajo) y «ab» '
        'empieza con la a.',
    categoria: GridCategory.silabas,
    difficulty: 2,
  ),
  porTextoObjetivo(
    id: 'SIL_pa',
    sectionLabel: 'BUSCA LA SÍLABA',
    question: 'Encuentra todas las «pa»',
    instruction: 'Toca cada «pa». La «ap» y la «ba» se le parecen.',
    celdas: const [
      'pa', 'ap', 'ba', 'pa', 'ap',
      'pa', 'ba', 'ap', 'pa', 'pa',
      'ap', 'ba', 'pa', 'ap', 'pa',
      'pa', 'ba', 'ap', 'pa', 'ba',
    ],
    objetivo: 'pa',
    explanation:
        '«pa» empieza con la p, que baja la panza. «ba» sube la panza y «ap» '
        'empieza con la a.',
    categoria: GridCategory.silabas,
    difficulty: 2,
  ),
];

/// Flechas: lateralidad. Se marca todas las que apuntan hacia la dirección
/// pedida. Es la ficha "Las flechas" del cuadernillo (p. 8).
final List<GridGame> kJuegosFlechas = [
  porTextoObjetivo(
    id: 'FLE_derecha',
    sectionLabel: 'LAS FLECHAS',
    question: 'Flechas que van a la derecha',
    instruction: 'Toca todas las flechas que apuntan a la derecha →.',
    celdas: const [
      '→', '←', '↑', '→', '↓',
      '→', '↑', '←', '→', '→',
      '↓', '→', '←', '↑', '→',
      '→', '↓', '←', '→', '↑',
    ],
    objetivo: '→',
    explanation:
        'La derecha es hacia donde apunta la flecha →. Es la mano con la que '
        'la mayoría escribe.',
    categoria: GridCategory.flechas,
  ),
  porTextoObjetivo(
    id: 'FLE_izquierda',
    sectionLabel: 'LAS FLECHAS',
    question: 'Flechas que van a la izquierda',
    instruction: 'Toca todas las flechas que apuntan a la izquierda ←.',
    celdas: const [
      '←', '→', '↓', '←', '↑',
      '←', '→', '←', '↓', '←',
      '↑', '←', '→', '←', '↓',
      '←', '↑', '→', '←', '→',
    ],
    objetivo: '←',
    explanation:
        'La izquierda es el lado contrario a la derecha. La flecha ← apunta '
        'hacia allá.',
    categoria: GridCategory.flechas,
    difficulty: 2,
  ),
  porTextoObjetivo(
    id: 'FLE_arriba',
    sectionLabel: 'LAS FLECHAS',
    question: 'Flechas que van hacia arriba',
    instruction: 'Toca todas las flechas que apuntan hacia arriba ↑.',
    celdas: const [
      '↑', '→', '↓', '↑', '←',
      '↑', '↓', '↑', '→', '↑',
      '←', '↑', '↓', '↑', '→',
      '↑', '←', '↓', '↑', '↓',
    ],
    objetivo: '↑',
    explanation:
        'Arriba es hacia el techo. La flecha ↑ apunta hacia allá; ↓ es lo contrario.',
    categoria: GridCategory.flechas,
    difficulty: 2,
  ),
];
```

Reemplazar el getter `kCuadernilloGridGames` por:

```dart
List<GridGame> get kCuadernilloGridGames => [
      ...kJuegosOrientacion,
      ...kJuegosSilabas,
      ...kJuegosFlechas,
    ];
```

- [ ] **Step 5: Run the full suite**

Run: `flutter test`
Expected: PASS — los invariantes previos cubren automáticamente los juegos nuevos; y las aserciones nuevas de sílabas/flechas pasan.

Run: `flutter analyze`
Expected: 0 nuevos.

- [ ] **Step 6: Commit**

```bash
git add lib/features/child/data/cuadernillo_grid_games.dart \
        lib/features/child/data/child_grid_games.dart \
        test/cuadernillo_grid_games_test.dart
git commit -m "feat(niño): cuadrículas de sílabas y flechas (cuadernillo)"
```

---

### Task 6: Catálogo de dos niveles y enganche desde el home

**Files:**
- Create: `lib/features/child/presentation/screens/child_games_catalog_screen.dart`
- Modify: `lib/features/child/presentation/screens/child_home_screen.dart` (el botón "Mis juegos" abre el catálogo)
- Test: `test/child_games_catalog_test.dart`

**Interfaces:**
- Consumes: `kTodosLosGridGames`, `GridGame`, `GridCategory` (Tasks 2-5); `ChildGridGameScreen(studentName, juegos)` (existente).
- Produces:
  - `class ChildGamesCatalogScreen extends StatelessWidget { final String studentName; final List<GridGame>? juegos; ChildGamesCatalogScreen({super.key, required this.studentName, List<GridGame>? juegos}); }` (el parámetro `juegos` permite inyectar en pruebas; por defecto `kTodosLosGridGames`).
  - Función pública `String nombreCategoria(GridCategory c)` para el título de cada sección.

- [ ] **Step 1: Write the failing test**

Crear `test/child_games_catalog_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:cognifit_mobile/features/child/data/child_grid_games.dart';
import 'package:cognifit_mobile/features/child/presentation/screens/child_games_catalog_screen.dart';
import 'package:cognifit_mobile/features/child/presentation/screens/child_grid_game_screen.dart';

void main() {
  GridGame juego(String id, String question, GridCategory cat) => GridGame(
        id: id,
        sectionLabel: 'X',
        question: question,
        instruction: 'i',
        celdas: List<GridCell>.filled(20, const TextCell('a'))..[0] = const TextCell('b'),
        objetivos: const {0},
        explanation: 'e',
        categoria: cat,
      );

  testWidgets('agrupa por categoría y muestra los títulos de los juegos', (t) async {
    final juegos = [
      juego('A', 'Encuentra las b', GridCategory.buscaLetra),
      juego('B', 'Encuentra las da', GridCategory.silabas),
    ];
    await t.pumpWidget(MaterialApp(
      home: ChildGamesCatalogScreen(studentName: 'Ana', juegos: juegos),
    ));
    expect(find.text(nombreCategoria(GridCategory.buscaLetra)), findsOneWidget);
    expect(find.text(nombreCategoria(GridCategory.silabas)), findsOneWidget);
    expect(find.text('Encuentra las b'), findsOneWidget);
    expect(find.text('Encuentra las da'), findsOneWidget);
  });

  testWidgets('tocar un juego abre la cuadrícula con solo ese juego', (t) async {
    final juegos = [
      juego('A', 'Encuentra las b', GridCategory.buscaLetra),
      juego('B', 'Encuentra las da', GridCategory.silabas),
    ];
    await t.pumpWidget(MaterialApp(
      home: ChildGamesCatalogScreen(studentName: 'Ana', juegos: juegos),
    ));
    await t.tap(find.text('Encuentra las b'));
    await t.pumpAndSettle();
    final screen =
        t.widget<ChildGridGameScreen>(find.byType(ChildGridGameScreen));
    expect(screen.juegos.length, 1);
    expect(screen.juegos.single.id, 'A');
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/child_games_catalog_test.dart`
Expected: FAIL de compilación — `ChildGamesCatalogScreen`/`nombreCategoria` no existen.

- [ ] **Step 3: Implementar el catálogo**

Crear `lib/features/child/presentation/screens/child_games_catalog_screen.dart`:

```dart
import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../data/child_grid_games.dart';
import 'child_grid_game_screen.dart';

/// Nombre visible de cada categoría en el catálogo.
String nombreCategoria(GridCategory c) => switch (c) {
      GridCategory.buscaLetra => 'Busca la letra',
      GridCategory.silabas => 'Busca la sílaba',
      GridCategory.flechas => 'Las flechas',
      GridCategory.orientacion => 'Misma orientación',
      GridCategory.cualEsDiferente => '¿Cuál es diferente?',
    };

/// Orden pedagógico: de lo más concreto (letras) a lo más abstracto.
const _ordenCategorias = [
  GridCategory.buscaLetra,
  GridCategory.silabas,
  GridCategory.flechas,
  GridCategory.orientacion,
  GridCategory.cualEsDiferente,
];

/// Catálogo de dos niveles: categoría → juegos. El niño elige un juego o toda
/// una categoría, en vez de recorrer una corrida lineal que se reinicia.
class ChildGamesCatalogScreen extends StatelessWidget {
  final String studentName;

  /// Permite inyectar otra lista en las pruebas.
  final List<GridGame> juegos;

  ChildGamesCatalogScreen({
    super.key,
    required this.studentName,
    List<GridGame>? juegos,
  }) : juegos = juegos ?? kTodosLosGridGames;

  void _jugar(BuildContext context, List<GridGame> seleccion) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ChildGridGameScreen(
          studentName: studentName,
          juegos: seleccion,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Agrupar respetando el orden pedagógico y sin categorías vacías.
    final porCategoria = <GridCategory, List<GridGame>>{};
    for (final cat in _ordenCategorias) {
      final delGrupo = juegos.where((j) => j.categoria == cat).toList();
      if (delGrupo.isNotEmpty) porCategoria[cat] = delGrupo;
    }

    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(title: const Text('Mis juegos')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          for (final entry in porCategoria.entries) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 12, 4, 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(nombreCategoria(entry.key),
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800, color: AppTheme.primary)),
                  if (entry.value.length > 1)
                    TextButton(
                      onPressed: () => _jugar(context, entry.value),
                      child: const Text('Jugar todos'),
                    ),
                ],
              ),
            ),
            for (final j in entry.value)
              Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text(j.question,
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => _jugar(context, [j]),
                ),
              ),
          ],
        ],
      ),
    );
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/child_games_catalog_test.dart`
Expected: PASS (2 tests).

- [ ] **Step 5: Enganchar el catálogo desde el home**

En `lib/features/child/presentation/screens/child_home_screen.dart`, agregar el import:

```dart
import 'child_games_catalog_screen.dart';
```

En el `_ActivityCard` de "Mis juegos", reemplazar el `onTap` que hoy abre `ChildGridGameScreen` por:

```dart
              onTap: () => Navigator.push(context, MaterialPageRoute(
                builder: (_) => ChildGamesCatalogScreen(studentName: studentName),
              )),
```

Si tras el cambio `ChildGridGameScreen` deja de estar importado en este archivo y el analizador lo marca como import sin usar, quitar `import 'child_grid_game_screen.dart';` de `child_home_screen.dart`.

- [ ] **Step 6: Run the full suite**

Run: `flutter test`
Expected: PASS.

Run: `flutter analyze`
Expected: 0 nuevos.

- [ ] **Step 7: Commit**

```bash
git add lib/features/child/presentation/screens/child_games_catalog_screen.dart \
        lib/features/child/presentation/screens/child_home_screen.dart \
        test/child_games_catalog_test.dart
git commit -m "feat(niño): catálogo de juegos por categoría en vez de corrida lineal"
```

---

## Verificación final (después de las 6 tareas)

- [ ] `flutter test` — toda la suite en verde.
- [ ] `flutter analyze` — 0 errores/warnings nuevos.
- [ ] Recorrido manual: modo niño → "Mis juegos" abre el catálogo; se ve al menos una categoría por cada `GridCategory` con contenido; tocar un juego lo abre solo a él; "Jugar todos" abre la categoría; salir regresa al catálogo (sin reiniciar nada).
- [ ] Los 28 juegos previos siguen presentes y jugables (en `Busca la letra` y `¿Cuál es diferente?`).
