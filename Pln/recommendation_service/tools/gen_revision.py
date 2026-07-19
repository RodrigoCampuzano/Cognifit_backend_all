"""Genera el paquete de revisión desde los bancos, para que lo que revise el
especialista sea exactamente lo que la app entrega — no una copia a mano."""
import html
import json
from pathlib import Path

DATA = Path("/home/rodrigo/Documentos/Cognifit/Pln/recommendation_service/data")
SALIDA = Path(__file__).with_name("revision_comprension.html")

SEP = {'1': (35, 59), '2': (60, 84), '3': (85, 99),
       '4': (100, 114), '5': (115, 124), '6': (125, 134)}

HABILIDAD = {
    'comprension_literal': 'Localizar información explícita',
    'verdadero_falso': 'Contrastar afirmaciones con el texto',
    'secuencia': 'Ordenar los hechos en el tiempo',
    'referentes': 'A quién sustituye cada pronombre',
    'homofonos': 'Homófonos según el sentido',
    'coherencia': 'Encontrar la frase que no encaja',
    'inferencia_causal': 'Deducir causas no escritas',
    'prediccion': 'Anticipar a partir de pistas',
    'idea_principal': 'Idea principal frente a detalle',
    'lenguaje_figurado': 'Refranes y frases figuradas',
    'hecho_opinion': 'Distinguir lo comprobable de lo opinable',
    'resumen': 'Elegir el resumen que no se queda corto',
    'vocabulario_contexto': 'Deducir palabras por contexto',
    'comparacion_textos': 'Contrastar dos textos del mismo tema',
    'intencion_sesgo': 'Detectar intención y sesgo',
    'verificacion': 'Lo dice / lo contradice / no habla de eso',
    'texto_discontinuo': 'Leer un instructivo',
    'organizacion_informacion': 'Ubicar información en categorías',
    'metacognicion': 'Predecir el desempeño y comparar',
    'fluidez_comprension': 'Lectura silenciosa + comprensión',
}

TITULO_GRADO = {
    '4': ('4º grado', 'Comprensión literal — localizar lo que está escrito'),
    '5': ('5º grado', 'Comprensión inferencial — deducir lo que no está'),
    '6': ('6º grado', 'Comprensión crítica — evaluar lo que se dice y cómo'),
}


def e(s):
    return html.escape(str(s))


def parrafos(texto):
    return "".join(f"<p>{e(p)}</p>" for p in texto.split("\n") if p.strip())


def bloque_ejercicio(ex, n):
    hab = HABILIDAD.get(ex["subtipo"], ex["subtipo"])
    meta = ex.get("meta_palabras_por_minuto")
    nota = ""
    if meta:
        nota = (f'<p class="nota"><span class="etq">Velocidad</span> '
                f'Se compara contra <strong>{meta} ppm</strong>, el mínimo SEP de '
                f'{e(ex["grados"][0])}º medido en voz alta. Acá la lectura es '
                f'silenciosa, así que funciona como piso, no como meta.</p>')

    preguntas = []
    for it in ex["items"]:
        opts = "".join(
            f'<li class="{"ok" if o == it["correcta"] else ""}">{e(o)}</li>'
            for o in it["opciones"])
        preguntas.append(
            f'<li class="preg"><p class="enunciado">{e(it["estimulo"])}</p>'
            f'<ul class="opts">{opts}</ul></li>')

    return f"""
    <article class="ej">
      <header>
        <span class="num">{n}</span>
        <div>
          <h3>{e(ex["titulo"])}</h3>
          <p class="hab">{e(hab)}</p>
        </div>
      </header>
      <div class="lectura">{parrafos(ex["texto"])}</div>
      <p class="meta-lectura">{len(ex["texto"].split())} palabras · {len(ex["items"])} preguntas</p>
      {nota}
      <ol class="preguntas">{"".join(preguntas)}</ol>
    </article>"""


def main():
    comp = json.loads((DATA / "banco_comprension_universal.json").read_text("utf-8"))
    inter = json.loads((DATA / "banco_ejercicios_intervencion.json").read_text("utf-8"))

    por_grado = {}
    for ex in comp["ejercicios"]:
        por_grado.setdefault(ex["grados"][0], []).append(ex)

    secciones = []
    for g in sorted(por_grado):
        titulo, bajada = TITULO_GRADO[g]
        cuerpo = "".join(bloque_ejercicio(ex, i + 1)
                         for i, ex in enumerate(por_grado[g]))
        secciones.append(f"""
        <section class="grado" id="g{g}">
          <div class="grado-head">
            <h2>{e(titulo)}</h2>
            <p>{e(bajada)}</p>
          </div>
          {cuerpo}
        </section>""")

    # Metas de intervención por debajo del estándar nacional.
    filas = []
    for ex in inter["ejercicios"]:
        if "sep_estandar_por_grado" not in ex:
            continue
        m = ex.get("meta_palabras_por_minuto") or ex.get("velocidad_palabras_por_minuto")
        bajo = set(ex.get("meta_bajo_estandar_sep", []))
        celdas = []
        for g in sorted(ex["sep_estandar_por_grado"]):
            lo, hi = SEP[g]
            cls = "gap" if g in bajo else "ok"
            celdas.append(f'<span class="banda {cls}">{g}º {lo}–{hi}</span>')
        filas.append(
            f'<tr><td><code>{e(ex["exercise_id"])}</code></td>'
            f'<td class="num-col">{m}</td>'
            f'<td>{"".join(celdas)}</td></tr>')

    total_ej = len(comp["ejercicios"])
    total_preg = sum(len(x["items"]) for x in comp["ejercicios"])

    doc = f"""<title>Revisión — Banco de comprensión lectora</title>
<style>
  :root {{
    --paper:#FBFCFD; --card:#FFFFFF; --ink:#16202E; --muted:#5C6B7A;
    --rule:#DCE3EA; --primary:#1B4B5A; --query:#8A5B00;
    --ok:#2F6B4F; --gap:#A33A2E; --ok-bg:#EAF3EE; --gap-bg:#FBEDEB;
    --query-bg:#FBF3E2;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --paper:#11161C; --card:#171E26; --ink:#E8EDF2; --muted:#97A5B4;
      --rule:#29323D; --primary:#6FB3C4; --query:#D9A63A;
      --ok:#6FBF95; --gap:#E0857A; --ok-bg:#1B2A24; --gap-bg:#2C1D1B;
      --query-bg:#2A2318;
    }}
  }}
  :root[data-theme="dark"] {{
    --paper:#11161C; --card:#171E26; --ink:#E8EDF2; --muted:#97A5B4;
    --rule:#29323D; --primary:#6FB3C4; --query:#D9A63A;
    --ok:#6FBF95; --gap:#E0857A; --ok-bg:#1B2A24; --gap-bg:#2C1D1B;
    --query-bg:#2A2318;
  }}
  :root[data-theme="light"] {{
    --paper:#FBFCFD; --card:#FFFFFF; --ink:#16202E; --muted:#5C6B7A;
    --rule:#DCE3EA; --primary:#1B4B5A; --query:#8A5B00;
    --ok:#2F6B4F; --gap:#A33A2E; --ok-bg:#EAF3EE; --gap-bg:#FBEDEB;
    --query-bg:#FBF3E2;
  }}

  body {{
    background: var(--paper); color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6; margin: 0; padding: 0 20px 80px;
    -webkit-text-size-adjust: 100%;
  }}
  .wrap {{ max-width: 44rem; margin: 0 auto; }}

  .head {{ padding: 56px 0 32px; border-bottom: 2px solid var(--ink); margin-bottom: 40px; }}
  .kicker {{
    font-size: .74rem; letter-spacing: .13em; text-transform: uppercase;
    color: var(--primary); font-weight: 700; margin: 0 0 12px;
  }}
  h1 {{ font-size: 2.1rem; line-height: 1.15; margin: 0 0 14px; text-wrap: balance; letter-spacing: -.02em; }}
  .sub {{ color: var(--muted); margin: 0; font-size: 1.02rem; }}
  .cifras {{ display: flex; flex-wrap: wrap; gap: 28px; margin-top: 26px; }}
  .cifra b {{ display: block; font-size: 1.6rem; line-height: 1; font-variant-numeric: tabular-nums; }}
  .cifra span {{ font-size: .8rem; color: var(--muted); }}

  h2 {{ font-size: 1.4rem; margin: 0 0 6px; letter-spacing: -.01em; }}
  section {{ margin-bottom: 56px; }}

  .pide {{ background: var(--query-bg); border-radius: 12px; padding: 26px 28px; }}
  .pide h2 {{ color: var(--query); }}
  .pide ol {{ margin: 18px 0 0; padding-left: 22px; }}
  .pide li {{ margin-bottom: 15px; }}
  .pide li:last-child {{ margin-bottom: 0; }}
  .pide strong {{ display: block; }}
  .pide p {{ margin: 3px 0 0; color: var(--muted); font-size: .93rem; }}

  table {{ width: 100%; border-collapse: collapse; margin-top: 18px; font-size: .9rem; }}
  th, td {{ text-align: left; padding: 11px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
  th {{ font-size: .72rem; letter-spacing: .09em; text-transform: uppercase; color: var(--muted); }}
  .num-col {{ font-variant-numeric: tabular-nums; font-weight: 700; }}
  code {{ font-size: .84em; word-break: break-all; }}
  .tabla-scroll {{ overflow-x: auto; }}

  .banda {{
    display: inline-block; font-size: .78rem; padding: 2px 8px; border-radius: 20px;
    margin: 0 5px 5px 0; font-variant-numeric: tabular-nums; white-space: nowrap;
  }}
  .banda.ok {{ background: var(--ok-bg); color: var(--ok); }}
  .banda.gap {{ background: var(--gap-bg); color: var(--gap); font-weight: 700; }}

  .grado-head {{ border-left: 3px solid var(--primary); padding-left: 16px; margin-bottom: 30px; }}
  .grado-head p {{ margin: 0; color: var(--muted); }}

  .ej {{
    background: var(--card); border: 1px solid var(--rule); border-radius: 14px;
    padding: 24px 26px; margin-bottom: 20px;
  }}
  .ej header {{ display: flex; gap: 14px; align-items: baseline; margin-bottom: 18px; }}
  .num {{
    font-variant-numeric: tabular-nums; font-size: .8rem; font-weight: 700;
    color: var(--primary); border: 1px solid var(--rule); border-radius: 50%;
    min-width: 26px; height: 26px; display: grid; place-items: center; flex: none;
  }}
  .ej h3 {{ font-size: 1.1rem; margin: 0; }}
  .hab {{ margin: 2px 0 0; font-size: .86rem; color: var(--muted); }}

  /* El texto se muestra en serif y con interlínea amplia, como lo ve el alumno
     en la app: lo que se revisa es la lectura, no una transcripción. */
  .lectura {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.05rem; line-height: 1.85;
    border-left: 2px solid var(--rule); padding-left: 18px; margin-bottom: 10px;
  }}
  .lectura p {{ margin: 0 0 .9em; }}
  .lectura p:last-child {{ margin-bottom: 0; }}
  .meta-lectura {{ font-size: .78rem; color: var(--muted); margin: 0 0 16px; }}

  .nota {{
    background: var(--query-bg); border-radius: 9px; padding: 12px 14px;
    font-size: .88rem; margin: 0 0 18px;
  }}
  .etq {{
    font-size: .68rem; letter-spacing: .1em; text-transform: uppercase;
    color: var(--query); font-weight: 700; margin-right: 8px;
  }}

  .preguntas {{ margin: 0; padding-left: 20px; }}
  .preg {{ margin-bottom: 16px; }}
  .preg:last-child {{ margin-bottom: 0; }}
  .enunciado {{ margin: 0 0 7px; font-weight: 600; }}
  .opts {{ list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 6px; }}
  .opts li {{
    font-size: .87rem; padding: 4px 11px; border-radius: 20px;
    border: 1px solid var(--rule); color: var(--muted);
  }}
  .opts li.ok {{
    background: var(--ok-bg); color: var(--ok); border-color: transparent; font-weight: 700;
  }}
  .opts li.ok::before {{ content: "✓ "; }}

  .cierre {{ border-top: 1px solid var(--rule); padding-top: 26px; }}
  .cierre h2 {{ font-size: 1.15rem; }}
  .cierre p {{ color: var(--muted); }}
  .fuente {{ font-size: .82rem; color: var(--muted); margin-top: 34px; }}
  .fuente a {{ color: var(--primary); }}

  @media (max-width: 560px) {{
    h1 {{ font-size: 1.65rem; }}
    .ej {{ padding: 20px 18px; }}
    .pide {{ padding: 20px 18px; }}
  }}
</style>

<div class="wrap">
  <div class="head">
    <p class="kicker">CogniFit Escolar · Para revisión docente</p>
    <h1>Banco de comprensión lectora</h1>
    <p class="sub">Los {total_ej} textos que la app entrega a 4º, 5º y 6º, tal como los ve el alumno.
    Nada de esto se ha usado con niños todavía.</p>
    <div class="cifras">
      <div class="cifra"><b>{total_ej}</b><span>ejercicios</span></div>
      <div class="cifra"><b>{total_preg}</b><span>preguntas</span></div>
      <div class="cifra"><b>3</b><span>grados</span></div>
    </div>
  </div>

  <section class="pide">
    <h2>Lo que necesito que decidas</h2>
    <ol>
      <li><strong>¿El vocabulario y los contextos funcionan en Chiapas?</strong>
        <p>Los textos hablan de café, ámbar de Simojovel, meliponas, almácigos y las
        regiones del estado. Quien los escribió no conoce la región de primera mano:
        esto es lo que menos puedo verificar solo.</p></li>
      <li><strong>¿La dificultad corresponde al grado?</strong>
        <p>Los textos van de 51 a 160 palabras, creciendo con el grado. Hay palabras
        técnicas —sedimentos, vestigios, jobones, meliponas— explicadas en contexto.</p></li>
      <li><strong>¿La progresión 4º → 5º → 6º está bien planteada?</strong>
        <p>Literal, después inferencial, después crítica. Un alumno que no resuelve lo
        literal difícilmente resuelva lo inferencial, así que 4º no es material “para
        los chicos”: es el piso que conviene verificar aunque al alumno le toque 6º.</p></li>
      <li><strong>Las metas de velocidad de los ejercicios de intervención</strong>
        <p>Ver la sección siguiente. Es la decisión con consecuencia más directa:
        hoy determina si un alumno sube de nivel.</p></li>
    </ol>
  </section>

  <section>
    <h2>Velocidad de lectura</h2>
    <p class="sub">Los Estándares Nacionales de Habilidad Lectora de la SEP fijan, por grado,
    cuántas palabras por minuto debería leer un alumno <strong>en voz alta</strong>.
    Contrasté las metas del banco contra esa tabla.</p>

    <div class="tabla-scroll">
      <table>
        <thead><tr><th>Ejercicio de intervención</th><th>Meta actual</th><th>Estándar SEP de sus grados</th></tr></thead>
        <tbody>{"".join(filas)}</tbody>
      </table>
    </div>

    <p style="margin-top:20px">En rojo, los grados donde la meta del ejercicio queda
    <strong>por debajo del mínimo nacional</strong>. Puede ser un hito remedial
    deliberado —a un alumno de 5º con dificultad severa no se le pone 115 ppm como
    primera meta— pero hoy la app le dice “¡Alcanzaste la meta!” y la ruta lo sube de
    nivel sin señalar en ningún lado la distancia que falta hasta el estándar de su grado.</p>

    <p><strong>La pregunta concreta:</strong> ¿esas metas son hitos remediales correctos,
    y basta con mostrar también el estándar del grado? ¿O hay que subirlas?</p>
  </section>

  {"".join(secciones)}

  <section class="cierre">
    <h2>Lo que no pude resolver</h2>
    <p>Los textos son originales, escritos para este banco. No se copió material de
    bancos de fichas: son gratuitos para uso docente, pero eso no autoriza a
    redistribuirlos dentro de una app.</p>
    <p>Las situaciones cotidianas —el mercado, el camión que se va, el patio de tierra
    de la escuela— se escribieron sin marcas de clase social ni de ciudad, porque un
    alumno que no se reconoce en el texto lee peor. Si algo suena ajeno o postizo,
    ese es exactamente el tipo de corrección que hace falta.</p>
    <p class="fuente">Estándares de velocidad:
      <a href="https://www.gob.mx/sep/acciones-y-programas/estandares-nacionales-de-habilidad-lectora-habilidad-lectora">SEP — Estándares Nacionales de Habilidad Lectora</a>.
      Se miden en lectura en voz alta.
    </p>
  </section>
</div>"""

    SALIDA.write_text(doc, encoding="utf-8")
    print(f"escrito: {SALIDA}  ({len(doc):,} bytes)")
    print(f"ejercicios: {total_ej}  preguntas: {total_preg}  filas ppm: {len(filas)}")


if __name__ == "__main__":
    main()
