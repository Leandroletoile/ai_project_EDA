"""Dashboard interactivo del EDA de COVID-19 en EE. UU.

Ejecutar desde la raíz del repositorio (con los datos ya procesados):

    python -m src.run_processing      # solo la primera vez
    streamlit run app.py

El CEO puede elegir indicador, estados, tamaño de estado y periodo, y explorar cuatro vistas:
evolución en el tiempo, ranking, mapa y calidad de los datos.
Todos los cálculos están en src/dashboard_data.py (con tests); aquí solo se dibuja.
"""
import sys
from datetime import date
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src import dashboard_data as dd  # noqa: E402

# Primero el CSV generado por el pipeline; si no existe (p. ej. en la nube), la copia comprimida del repo.
PROCESSED_FILE = ROOT / "data" / "processed" / "covid_clean.csv"
SNAPSHOT_FILE = ROOT / "data" / "dashboard" / "covid_clean.csv.gz"
QUALITY_MD = ROOT / "reports" / "data_quality" / "informe_calidad_datos.md"
QUALITY_JSON = QUALITY_MD.with_suffix(".json")

st.set_page_config(page_title="COVID-19 en EE. UU.", page_icon="📊", layout="wide")


def es(n) -> str:
    """12345 -> 12.345 (miles con punto)."""
    return f"{n:,.0f}".replace(",", ".")


@st.cache_data
def get_data(path: str):
    return dd.load_processed(path)


DATA_FILE = dd.first_existing([PROCESSED_FILE, SNAPSHOT_FILE])
if DATA_FILE is None:
    st.error("Todavía no hay datos procesados. Ejecuta en la terminal: `python -m src.run_processing`")
    st.stop()

df = get_data(str(DATA_FILE))
nombres = df.drop_duplicates("state").set_index("state")["state_name"].dropna().to_dict()
estados = dd.states_with_population(df)

# ------------------------------------------------------------------ panel lateral
st.sidebar.header("Filtros")
metric_label = st.sidebar.selectbox("Indicador", list(dd.METRICS))
metric = dd.METRICS[metric_label]

por_defecto = [s for s in ["NY", "TX", "CA", "FL", "NJ", "ND"] if s in estados]
elegidos = st.sidebar.multiselect(
    "Estados (para Evolución, Datos y cifras de cabecera)",
    estados,
    default=por_defecto,
    format_func=lambda s: f"{nombres.get(s, s)} ({s})",
)
tamanos = st.sidebar.multiselect(
    "Tamaño del estado",
    dd.SIZE_ORDER,
    default=dd.SIZE_ORDER,
    help="Cuartiles de población: Pequeño es el 25 % de estados con menos habitantes.",
)
fecha_min, fecha_max = df["date"].min().date(), df["date"].max().date()
inicio, fin = st.sidebar.slider(
    "Periodo",
    min_value=fecha_min,
    max_value=fecha_max,
    value=(max(date(2020, 3, 1), fecha_min), fecha_max),
    format="DD/MM/YYYY",
)
st.sidebar.caption("Fuente: COVID Tracking Project. Población: Census 2019. Datos hasta el 7-mar-2021.")

sel = dd.filter_data(df, states=elegidos, start=inicio, end=fin, sizes=tamanos)

# ------------------------------------------------------------------ cabecera
st.title("COVID-19 en Estados Unidos")
st.caption("Explora la evolución por estado. Los indicadores «por 100.000 hab.» permiten comparar estados de distinto tamaño.")

k = dd.kpis(sel)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Casos acumulados", es(k["cases"]))
c2.metric("Fallecimientos acumulados", es(k["deaths"]))
c3.metric("Letalidad aparente", "—" if k["cfr"] != k["cfr"] else f"{k['cfr']:.1f} %".replace(".", ","))
c4.metric("Estados incluidos", str(k["n_states"]))

tab_evo, tab_rank, tab_map, tab_cal, tab_dat = st.tabs(
    ["Evolución", "Ranking", "Mapa", "Calidad de los datos", "Datos"]
)

# ------------------------------------------------------------------ evolución
with tab_evo:
    if not elegidos:
        st.info("Elige al menos un estado en el panel de la izquierda.")
    else:
        serie = sel.dropna(subset=[metric])
        if serie.empty:
            st.info("Este indicador no tiene datos en el periodo elegido (algunos necesitan 7 días de historia).")
        else:
            fig = px.line(
                serie, x="date", y=metric, color="state_name",
                labels={"date": "Fecha", metric: metric_label, "state_name": "Estado"},
                title=metric_label,
            )
            fig.update_layout(hovermode="x unified", template="simple_white", legend_title_text="Estado")
            st.plotly_chart(fig)
        st.caption("Las medias de 7 días suavizan el efecto del día de la semana y los datos atrasados.")

# ------------------------------------------------------------------ ranking
with tab_rank:
    pool = dd.filter_data(df, sizes=tamanos, start=inicio, end=fin)
    snap = dd.snapshot(pool, metric, as_of=fin)
    cuantos = st.slider("Cuántos estados mostrar", 5, 51, 15)
    top = snap.head(cuantos).iloc[::-1]  # al revés para que el primero quede arriba en la barra horizontal
    if top.empty:
        st.info("No hay datos para este indicador en la fecha elegida.")
    else:
        fig = px.bar(
            top, x=metric, y="state_name", orientation="h",
            labels={metric: metric_label, "state_name": ""},
            title=f"{metric_label} · al {fin:%d/%m/%Y}",
        )
        fig.update_layout(template="simple_white", height=max(350, 24 * len(top) + 120))
        st.plotly_chart(fig)
    st.caption("El ranking incluye todos los estados del tamaño elegido, no solo los marcados a la izquierda.")

# ------------------------------------------------------------------ mapa
with tab_map:
    mapa = dd.snapshot(dd.filter_data(df, sizes=tamanos, start=inicio, end=fin), metric, as_of=fin)
    if mapa.empty:
        st.info("No hay datos para este indicador en la fecha elegida.")
    else:
        fig = px.choropleth(
            mapa, locations="state", locationmode="USA-states", color=metric, scope="usa",
            hover_name="state_name", color_continuous_scale="Blues",
            labels={metric: metric_label},
            title=f"{metric_label} · al {fin:%d/%m/%Y}",
        )
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig)

# ------------------------------------------------------------------ calidad
with tab_cal:
    rep = dd.load_quality_report(QUALITY_JSON)
    if rep:
        q1, q2, q3 = st.columns(3)
        q1.metric("Filas procesadas", es(rep["rows_out"]))
        q2.metric("Columnas descartadas", str(len(rep["columns_dropped"])))
        q3.metric("Registros con correcciones", es(rep["rows_with_correction"]))
    if QUALITY_MD.exists():
        st.markdown(QUALITY_MD.read_text(encoding="utf-8"))
    else:
        st.info("Todavía no hay informe de calidad. Genéralo con `python -m src.run_processing`.")

# ------------------------------------------------------------------ datos
with tab_dat:
    columnas = ["date", "state", "state_name", "cases_cum", "deaths_cum", "new_cases", "new_deaths",
                "new_cases_7d", "new_deaths_7d", "cases_per_100k", "deaths_per_100k",
                "positivity_7d", "cfr", "correction_flag"]
    tabla = sel[[c for c in columnas if c in sel.columns]]
    st.dataframe(tabla)
    st.download_button("Descargar CSV filtrado", tabla.to_csv(index=False).encode("utf-8"),
                       file_name="covid_filtrado.csv", mime="text/csv")
