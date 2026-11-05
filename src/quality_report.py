"""Genera el informe de calidad de datos (Markdown) a partir de lo que hizo la limpieza."""
from __future__ import annotations

import pandas as pd


def md_table(headers: list[str], rows: list[list]) -> str:
    """Tabla Markdown sencilla (sin depender de `tabulate`)."""
    lines = ["| " + " | ".join(str(h) for h in headers) + " |",
             "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def _fmt(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def build_quality_report(raw: pd.DataFrame, clean: pd.DataFrame, rep: dict) -> str:
    """Informe con tres bloques: qué faltaba, qué se corrigió y qué quedó pendiente (y por qué)."""
    miss = (raw.isna().mean() * 100).round(1)
    dropped = rep["columns_dropped"]

    out = [
        "# Informe de calidad de datos",
        "",
        f"Dataset: COVID Tracking Project, `states/daily` · {_fmt(rep['rows_in'])} filas y "
        f"{rep['columns_in']} columnas de entrada · {rep['n_states']} jurisdicciones · "
        f"{rep['date_min']} a {rep['date_max']}.",
        f"Tras la limpieza: {_fmt(rep['rows_out'])} filas y {rep['columns_out']} columnas.",
        "",
        "## Qué faltaba",
        "",
    ]

    kept_missing = [(c, miss[c]) for c in raw.columns if c not in dropped and miss[c] > 0]
    kept_missing.sort(key=lambda x: -x[1])
    out.append("Columnas conservadas con valores faltantes (% de filas vacías en el original):")
    out.append("")
    out.append(md_table(["Columna", "% vacío"], [[c, f"{v}"] for c, v in kept_missing]))
    out += ["", f"Además se descartaron {len(dropped)} columnas (ver abajo). "
            "Los huecos de `positive` y `death` se concentran casi todos en las primeras "
            "semanas de 2020, antes de que cada estado empezara a reportar.", ""]

    out += ["## Qué se corrigió", ""]
    out.append(f"- **Duplicados:** {rep['duplicates_removed']} (la clave estado + fecha es única).")
    out.append("- **Tipo de dato:** `date` pasó de entero `YYYYMMDD` a fecha real.")
    out.append("- **Columnas descartadas**, agrupadas por motivo:")
    out.append("")
    by_reason: dict[str, list[str]] = {}
    for col, reason in dropped.items():
        by_reason.setdefault(reason, []).append(f"`{col}` ({miss[col]} % vacío)")
    out.append(md_table(["Motivo", "Columnas"], [[r, ", ".join(c)] for r, c in by_reason.items()]))
    out.append("")
    nf = rep["nulls_filled"]
    out.append("- **Huecos en acumulados:** relleno con el último valor conocido dentro de cada estado "
               "y, antes del primer reporte, con 0 (solo casos y muertes). Valores rellenados: "
               + ", ".join(f"`{k}` {_fmt(v)}" for k, v in nf.items()) + ".")
    nn = rep["negative_increments_fixed"]
    out.append("- **Incrementos diarios negativos** (correcciones que hacen los estados): se dejaron en 0 y la fila "
               f"quedó marcada en `correction_flag` ({_fmt(rep['rows_with_correction'])} filas). Por columna: "
               + ", ".join(f"`{k}` {_fmt(v)}" for k, v in nn.items()) + ".")
    out.append("- **Territorios** (AS, GU, MP, PR, VI): se marcan en `is_territory` para separarlos de los 50 estados + DC.")
    out.append("")

    out += ["## Qué quedó pendiente y por qué", ""]
    left = rep["nulls_left"]
    out.append(f"- **`tests_cum` sin valor al inicio** ({_fmt(left.get('tests_cum', 0))} filas): no se imputa con 0 "
               "porque un estado puede haber hecho pruebas antes de reportarlas; se deja vacío.")
    out.append("- **Ingresos hospitalarios actuales** (`hosp_now`, `icu_now`, `vent_now`): vacío significa "
               "\"no reportado\", no \"cero\"; imputar crearía una realidad que no está en la fuente.")
    out.append(f"- **Positivos > pruebas** en {_fmt(rep['cases_gt_tests_rows'])} filas: valor imposible (puede deberse "
               "a que casos y pruebas se miden en unidades distintas o con retraso). Se marcan en `cases_gt_tests`, "
               "no se corrigen porque no hay forma de saber cuál de las dos cifras está mal.")
    out.append("- **Unidades de las pruebas distintas por estado** (`tests_source`): unos cuentan personas, otros "
               "pruebas o encuentros. Por eso la positividad solo es aproximada y no debe compararse "
               "al milímetro entre estados.")
    if "positivity_over_100_rows" in rep:
        out.append(f"- **Positividad imposible (> 100 %)** en {_fmt(rep['positivity_over_100_rows'])} filas: "
                   "en esa semana hay más casos nuevos que pruebas nuevas. En la variable derivada "
                   "`positivity_7d` se convierten en vacío (NaN); las columnas originales no se tocan.")
    out.append("- **Picos diarios muy por encima de la media del estado**: probablemente cargas de datos "
               "atrasados o reclasificaciones (el dataset no lo confirma). Se conservan porque son valores de "
               "la fuente, se suavizan con medias de 7 días y se avisan en el análisis. Mayores saltos diarios "
               "de muertes en el original:")
    out.append("")
    top = raw.nlargest(5, "deathIncrease")[["state", "date", "deathIncrease"]]
    out.append(md_table(
        ["Estado", "Fecha", "Muertes en un día"],
        [[r.state, pd.to_datetime(str(r.date), format="%Y%m%d").date(), _fmt(r.deathIncrease)]
         for r in top.itertuples()]))
    out.append("")
    out.append("- **Población (2ª fuente)** solo para los 50 estados + DC: los territorios no entran en los "
               "análisis por 100.000 habitantes.")
    out.append("- **Los datos terminan el 7 de marzo de 2021**: cualquier conclusión sobre el efecto de las "
               "vacunas o de olas posteriores queda fuera del alcance de este dataset.")
    out.append("")
    return "\n".join(out)
