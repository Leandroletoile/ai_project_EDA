# COVID-19 en Estados Unidos · Proyecto EDA

Análisis exploratorio de la evolución diaria de la COVID-19 en los 50 estados, DC y 5 territorios de EE. UU. (13-ene-2020 → 7-mar-2021), desde los datos en bruto hasta un informe para dirección, un dashboard interactivo y un pipeline reproducible con un solo comando.

**Dashboard público:** https://aiprojecteda-zszpdnuedncp9t66n6ddvy.streamlit.app/

## Qué encontramos

- **No hubo una ola, hubo tres.** Primavera 2020, verano 2020 y un invierno 2020-21 que concentra tres de cada cuatro casos. El pico nacional fue el 11-ene-2021, con 246.419 casos en un día.
- **Los totales engañan.** California tiene el mayor total de fallecidos (54.124), pero por 100.000 habitantes queda en el puesto 29 de 51. El primero es Nueva Jersey (265).
- **La letalidad «bajó» de 4,4 % a 1,7 %, pero es aparente:** al hacerse más pruebas aparecen más casos leves. Con estos datos no se puede atribuir la bajada a un mejor tratamiento.
- **Los datos tienen defectos documentados:** 219 registros con incrementos negativos (correcciones de los estados), 59 con más positivos que pruebas y saltos por carga de datos atrasados. Todo está marcado, no escondido (ver `reports/data_quality/`).

## Fuentes de datos

| Fuente | Uso | Archivo |
|---|---|---|
| [COVID Tracking Project](https://covidtracking.com/) (API `states/daily`) | Casos, muertes, pruebas y hospitalizaciones por estado y día | `data/raw/covid_us_states_daily.csv` (se descarga, no se versiona) |
| Estimaciones de población del Censo de EE. UU., 2019 | Normalizar por 100.000 habitantes (segunda fuente, cruce por estado) | `data/external/population_2019.csv` |

El COVID Tracking Project dejó de actualizarse el 7 de marzo de 2021: el análisis cubre ese histórico y no la situación actual.

## Estructura

```
app.py                       Dashboard Streamlit
data/raw/                    Datos originales (ignorados por git)
data/external/               Población 2019
data/processed/              covid_clean.csv generado por el pipeline (ignorado por git)
data/dashboard/              Copia comprimida de los datos procesados, para publicar el dashboard
notebooks/01_...             Exploración inicial
notebooks/02_...             EDA completo: limpieza justificada, features, gráficos, conclusiones
reports/informe_ejecutivo.pdf   Informe de 2 páginas para dirección
reports/guion_presentacion_5min.md   Guion de la presentación
reports/data_quality/        Informe de calidad de datos (.md y .json)
reports/initial_audit/, temporal_audit/   Auditorías previas
reports/figures/             Figuras del notebook
src/                         Código reutilizable (ver abajo)
tests/                       Tests con pytest
```

Módulos de `src/`:

- `download_data.py` descarga el dataset.
- `audit_raw_data.py`, `analyze_missingness.py`, `analyze_state_coverage.py`, `analyze_data_quality.py`, `analyze_temporal_quality.py` son las auditorías (etapas 1-5).
- `clean_data.py` es la limpieza reutilizable.
- `build_features.py` calcula población, tasas por 100.000, medias de 7 días, letalidad, positividad, periodos y atípicos.
- `quality_report.py` genera el informe de calidad.
- `run_processing.py` encadena limpieza, variables nuevas y guardado.
- `run_pipeline.py` es el pipeline completo (6 etapas).
- `dashboard_data.py` contiene la lógica de filtros y cifras del dashboard (sin Streamlit, para poder probarla).

## Instalación

Necesitas Python 3.13 (probado con esa versión).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **Nota para Windows con Smart App Control activado:** el bloqueo de binarios sin firma puede impedir que `pandas` cargue si está instalado `pyarrow` (lo instala Streamlit). Si te pasa, ejecuta `pip uninstall -y pyarrow`: pandas, los tests, el pipeline y el notebook funcionan sin él. Para el dashboard usa el enlace público o ejecútalo en un entorno sin esa restricción.

## Cómo ejecutarlo

Todos los comandos, desde la raíz del repositorio y con el entorno activado.

**1. Pipeline completo (un solo comando)**

```powershell
python -m src.run_pipeline
```

Ejecuta 6 etapas: auditoría de datos en bruto, valores ausentes, cobertura por estado, calidad de datos, calidad temporal y, por último, limpieza + variables nuevas. Genera `data/processed/covid_clean.csv` y `reports/data_quality/informe_calidad_datos.md`. Si no tienes el dataset en `data/raw/`, descárgalo antes:

```powershell
python -c "from src.run_pipeline import run_pipeline; run_pipeline(download=True)"
```

Para ejecutar solo la limpieza y las variables nuevas: `python -m src.run_processing` (acepta `--download`).

**2. Tests**

```powershell
python -m pytest -q
```

Los tests de limpieza, variables nuevas, informe de calidad, pipeline y dashboard se escribieron antes que las funciones que prueban.

**3. Notebook**

```powershell
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 notebooks/02_eda_limpieza_y_analisis.ipynb
```

O ábrelo con `python -m jupyter lab`. Necesita que exista `data/raw/covid_us_states_daily.csv`. GitHub no muestra los gráficos interactivos de Plotly: ábrelo en Jupyter para verlos.

**4. Dashboard**

```powershell
python -m src.run_processing   # solo si aún no existe data/processed/covid_clean.csv
python -m streamlit run app.py
```

Si no encuentra `data/processed/covid_clean.csv`, usa la copia de `data/dashboard/`. Permite elegir indicador, estados, tamaño de estado y periodo, con vistas de evolución, ranking, mapa, calidad de datos y tabla descargable.

## Decisiones de limpieza (resumen)

- Se descartan 28 columnas: constantes, metadatos, redundantes o con más del 80 % de valores ausentes.
- Los acumulados faltantes se rellenan con el último valor del mismo estado; antes del primer reporte, casos y muertes valen 0. Las hospitalizaciones **no** se imputan: un hueco significa «no reportado».
- Los incrementos negativos (correcciones de los estados) se reemplazan por 0 y se marcan en `correction_flag`.
- Los valores imposibles (más positivos que pruebas, más muertes que casos) se marcan y no se borran. Una positividad superior al 100 % se anula en la variable derivada.
- Los valores extremos **no se eliminan**: son los picos de las olas. Se detectan con la regla del rango intercuartílico y se suavizan con medias de 7 días.
- Los territorios se marcan (`is_territory`) y se excluyen de las comparaciones por habitante, porque no tienen población en la segunda fuente.

El detalle cifrado está en `reports/data_quality/informe_calidad_datos.md`.

## Limitaciones

- Cada estado cuenta las «pruebas» de forma distinta, por lo que no se comparan pruebas entre estados.
- La letalidad es aparente (muertes entre casos confirmados) y depende de cuántas pruebas se hagan.
- Las relaciones entre variables se calculan con 51 puntos (uno por estado): sirven para plantear hipótesis, no para demostrar causas.
- Población de 2019, no de 2020.
