# COVID-19 en Estados Unidos · Proyecto EDA

Análisis exploratorio de la evolución diaria de la COVID-19 en los 50 estados, DC y 5 territorios de EE. UU. (13-ene-2020 → 7-mar-2021). Va desde los datos en bruto hasta un informe para dirección, un dashboard interactivo publicado y un pipeline reproducible con un solo comando.

**Dashboard público:** https://aiprojecteda-zszpdnuedncp9t66n6ddvy.streamlit.app/

Este README tiene dos partes: **qué se hizo y por qué** (pasos 0 a 10) y **cómo reproducirlo** (instalación y ejecución).

## Índice

1. [Objetivo y nivel alcanzado](#1-objetivo-y-nivel-alcanzado)
2. [Fuentes de datos](#2-fuentes-de-datos)
3. [Qué encontramos](#3-qué-encontramos)
4. [Cómo se hizo, paso a paso](#4-cómo-se-hizo-paso-a-paso)
5. [Instalación](#5-instalación)
6. [Cómo ejecutarlo](#6-cómo-ejecutarlo)
7. [Estructura del repositorio](#7-estructura-del-repositorio)
8. [Problemas encontrados y cómo se resolvieron](#8-problemas-encontrados-y-cómo-se-resolvieron)
9. [Limitaciones y trabajo futuro](#9-limitaciones-y-trabajo-futuro)
10. [Tecnologías](#10-tecnologías)

---

## 1. Objetivo y nivel alcanzado

El enunciado plantea un equipo de datos al que un CEO entrega un conjunto de datos que nadie ha mirado con calma. Pide datos limpios, con sentido y la historia que hay detrás. El CEO no lee código: lee su informe.

Elegimos el dataset del **COVID Tracking Project** y llegamos al **nivel Experto**, que incluye los tres anteriores:

| Nivel | Qué pedía | Dónde está |
| --- | --- | --- |
| Esencial | Estructura, ausentes, duplicados, tipos, columnas, análisis univariado y bivariado, 5 gráficos, preguntas respondidas, notebook ordenado | `notebooks/02_eda_limpieza_y_analisis.ipynb` (secciones 1, 2, 4, 6 y 12), 12 figuras en `reports/figures/` |
| Medio | Limpieza justificada, atípicos, groupby y pivot, 3 variables nuevas, heatmap de correlación, tendencias, informe de 1 a 2 páginas | Notebook (secciones 2, 3, 5, 7, 8 y 9) y `reports/informe_ejecutivo.pdf` |
| Avanzado | Normalizar por habitante, segunda fuente, datos de calidad dudosa, media móvil y escala log, comparar segmentos, Plotly, limpieza reutilizable | `src/build_features.py`, `src/clean_data.py`, notebook (secciones 3, 9, 10 y 11) |
| Experto | Dashboard, pipeline de un comando, tests, informe de calidad, presentación de 5 minutos, enlace público | `app.py`, `src/run_pipeline.py`, `tests/`, `reports/data_quality/`, `reports/guion_presentacion_5min.md`, enlace de arriba |

## 2. Fuentes de datos

| Fuente | Uso | Archivo |
| --- | --- | --- |
| [COVID Tracking Project](https://covidtracking.com/) (API `states/daily`) | Casos, muertes, pruebas y hospitalizaciones por estado y día | `data/raw/covid_us_states_daily.csv` (se descarga, no se versiona) |
| Estimaciones de población del Censo de EE. UU., 2019 | Normalizar por 100.000 habitantes (segunda fuente, cruce por estado) | `data/external/population_2019.csv` (51 filas: 50 estados y DC) |

El COVID Tracking Project dejó de actualizarse el 7 de marzo de 2021: el análisis cubre ese histórico y no la situación actual.

El dataset original tiene **20.780 filas y 56 columnas**, un registro por estado y por día, para 56 jurisdicciones.

## 3. Qué encontramos

- **No hubo una ola, hubo tres.** Primavera 2020 (unos 31.000 casos al día en abril), verano 2020 (unos 66.000 a finales de julio) y un invierno 2020-21 que concentra tres de cada cuatro casos. El pico nacional fue el 11-ene-2021, con **246.419 casos en un día**.
- **Los totales engañan.** California tiene el mayor total de fallecidos (54.124), pero por 100.000 habitantes queda en el puesto 29 de 51. El primero es Nueva Jersey (265) y el último Hawái (31).
- **La letalidad «bajó» de 4,4 % a 1,7 %, pero es aparente:** al hacerse más pruebas aparecen más casos leves y el divisor crece. Con estos datos no se puede atribuir la bajada a un mejor tratamiento.
- **Las pruebas no se pueden comparar entre estados:** cada uno las cuenta de forma distinta.
- **Los datos tienen defectos documentados:** 219 registros con incrementos negativos (correcciones de los estados), 59 con más positivos que pruebas y saltos por carga de datos atrasados (Ohio informó 4.484 muertes en tres días de febrero). Todo está marcado, no escondido.

## 4. Cómo se hizo, paso a paso

### Paso 0 · Preparar el repositorio y el flujo de trabajo

- Estructura de carpetas (`data/`, `src/`, `tests/`, `notebooks/`, `reports/`) y entorno virtual `.venv`.
- Control de versiones con **una rama por fase** y Pull Request hacia `main` con mensajes de commit claros (`feat:`, `docs:`):
  - `feature/data-audit`: auditoría de los datos en bruto.
  - `feature/data-cleaning`: limpieza, variables nuevas e informe de calidad.
  - `feature/eda-notebook`: notebook completo y figuras.
  - `feature/dashboard-and-report`: informe ejecutivo, guion, dashboard, etapa 6 del pipeline y README.
- `.gitignore` excluye los CSV de `data/raw/` y `data/processed/` (se regeneran con el pipeline).

### Paso 1 · Descargar y auditar (sin modificar nada)

`src/download_data.py` descarga el dataset de la API y lo guarda como CSV. Después, cinco auditorías **solo observan y escriben informes** en `reports/initial_audit/` y `reports/temporal_audit/`:

| Auditoría | Qué comprueba | Qué encontró |
| --- | --- | --- |
| `audit_raw_data.py` | Estructura, rango de fechas, duplicados | 20.780 filas, 56 columnas, 56 jurisdicciones, del 13-ene-2020 al 7-mar-2021, sin duplicados |
| `analyze_missingness.py` | Qué variables tienen datos y desde cuándo | `dataQualityGrade` y `grade` 100 % vacías; muchas columnas con más del 80 % de ausentes |
| `analyze_state_coverage.py` | Si todos los estados informan de todo | Algunos estados no informan de hospitalizados o de pruebas negativas |
| `analyze_data_quality.py` | Negativos y columnas constantes o vacías | Valores negativos en incrementos diarios y 5 columnas constantes |
| `analyze_temporal_quality.py` | Huecos, acumulados que bajan, extremos y coherencia diario-acumulado | Sin huecos en el calendario; 230 descensos de acumulados; 660 valores diarios extremos; los incrementos coinciden al 100 % con la diferencia entre acumulados |

### Paso 2 · Limpiar con decisiones justificadas

La regla fue **marcar, no esconder**. El código está en `src/clean_data.py`, como pasos pequeños que se encadenan en `clean_pipeline`:

| Decisión | Por qué |
| --- | --- |
| Convertir la fecha (AAAAMMDD) a fecha real | Para ordenar, agrupar por mes y calcular medias móviles |
| Quitar duplicados | No había, pero el paso protege si se descarga otra versión |
| Descartar 28 columnas | Constantes, metadatos, redundantes o con más del 80 % de ausentes |
| Renombrar a nombres claros (`positive` → `cases_cum`, `positiveIncrease` → `new_cases`) | Para que el código se lea sin diccionario |
| Rellenar huecos de acumulados con el último valor del mismo estado | Un acumulado no baja: si hoy no se reportó, se mantiene el último |
| Antes del primer reporte, casos y muertes valen 0 | El estado todavía no tenía ninguno |
| No rellenar hospitalizados, UCI ni ventiladores | Ahí un hueco significa «no reportado», no «cero» |
| Incrementos negativos a 0, marcados en `correction_flag` | Son correcciones de los estados; un día con casos negativos no existe |
| Valores imposibles marcados (`cases_gt_tests`, `deaths_gt_cases`), no borrados | No sabemos cuál de las dos cifras está mal |
| Territorios marcados con `is_territory` | No tienen población en la segunda fuente |
| Positividad superior al 100 % anulada solo en la variable derivada | El dato original se conserva |
| Valores extremos **no** eliminados | Son los picos de las olas; se detectan con IQR y se suavizan con medias de 7 días |

### Paso 3 · Segunda fuente y variables nuevas

`src/build_features.py` une la población (cruce por estado, que exige que cada estado aparezca una vez) y calcula:

| Variable | Qué es |
| --- | --- |
| `cases_per_100k`, `deaths_per_100k` | Acumulados por 100.000 habitantes |
| `new_cases_7d`, `new_deaths_7d` | Media móvil de 7 días dentro de cada estado |
| `new_cases_per_100k_7d`, `new_deaths_per_100k_7d` | Lo anterior por 100.000 habitantes |
| `cfr` | Letalidad aparente: muertes acumuladas entre casos acumulados |
| `positivity_7d` | Proporción de pruebas con resultado positivo en 7 días |
| `year_month`, `week`, `weekday` | Partes de la fecha |
| `period` | Pre-brote, Primavera 2020, Verano 2020 e Invierno 2020-21 |
| `pop_group` | Cuartiles de población: Pequeño, Mediano, Grande y Muy grande |

### Paso 4 · Explorar en el notebook

`notebooks/02_eda_limpieza_y_analisis.ipynb` tiene 70 celdas con texto explicativo entre el código y se ejecuta de arriba abajo sin errores:

| Sección | Contenido |
| --- | --- |
| 1 | Carga y comprensión inicial |
| 2 | Limpieza justificada |
| 3 | Segunda fuente y variables nuevas |
| 4 | Análisis univariado |
| 5 | Valores atípicos |
| 6 | Análisis bivariado |
| 7 | Agrupaciones y tablas dinámicas (`groupby`, `pivot_table`) |
| 8 | Correlaciones (heatmap) |
| 9 | Tendencias: media de 7 días y escala logarítmica |
| 10 | Comparación de segmentos por tamaño de estado |
| 11 | Gráficos interactivos con Plotly (líneas, mapa y mapa animado) |
| 12 | Respuesta por escrito a las 5 preguntas planteadas al inicio |
| 13 | Conclusiones |

Las 12 figuras estáticas se guardan en `reports/figures/` (`01_vacios_por_mes.png` hasta `12_heatmap_estado_mes.png`).

### Paso 5 · Informe de calidad de datos

`src/quality_report.py` redacta, con cifras, **qué faltaba, qué se corrigió y qué quedó pendiente y por qué**. Se regenera con cada ejecución en `reports/data_quality/informe_calidad_datos.md` y `.json`.

### Paso 6 · Informe ejecutivo y presentación

- `reports/informe_ejecutivo.pdf`: 2 páginas para una persona sin formación en datos, con cifras clave, dos gráficos y los límites de lo que se puede afirmar.
- `reports/guion_presentacion_5min.md`: guion cronometrado de 5 minutos, con el hallazgo principal y las preguntas que pueden hacer.

### Paso 7 · Pipeline reproducible

`python -m src.run_pipeline` ejecuta **6 etapas** en orden: 1 a 5 las auditorías y la 6 la limpieza con variables nuevas (`src/run_processing.py`). Genera `data/processed/covid_clean.csv` y el informe de calidad. Si falta el dataset, falla con un mensaje claro.

### Paso 8 · Tests con pytest

**95 tests** que cubren limpieza, variables nuevas, informe de calidad, procesamiento, pipeline y la lógica del dashboard. Las funciones de limpieza, variables nuevas, informe, procesamiento y dashboard se desarrollaron escribiendo primero el test y viéndolo fallar, y después la función. El historial de git agrupa test y código en el mismo commit.

### Paso 9 · Dashboard interactivo (Streamlit)

- `app.py` solo dibuja; todo lo que filtra o calcula vive en `src/dashboard_data.py`, que tiene tests.
- Panel lateral: indicador, estados, tamaño del estado y periodo.
- Cinco pestañas: **Evolución**, **Ranking**, **Mapa**, **Calidad de los datos** y **Datos** (con descarga del CSV filtrado).
- Lee `data/processed/covid_clean.csv` si existe; si no, usa la copia comprimida de `data/dashboard/covid_clean.csv.gz`.

### Paso 10 · Publicar el dashboard en Streamlit Community Cloud

Como los CSV procesados no se suben a git, el repositorio incluye una copia comprimida de 2 MB (`data/dashboard/covid_clean.csv.gz`). Los pasos fueron:

1. Entrar en https://share.streamlit.io con la cuenta de GitHub.
2. Pulsar **Create app → Deploy a public app from GitHub**.
3. Elegir el repositorio `Leandroletoile/ai_project_EDA`, la rama `feature/dashboard-and-report` y el archivo principal `app.py`.
4. En **Advanced settings**, elegir **Python 3.13** (la misma versión usada en local).
5. Pulsar **Deploy**. Streamlit instala las dependencias desde `requirements.txt` (por eso incluye `streamlit` y `plotly`).

> **Importante:** la app queda desplegada desde esa rama. No se debe borrar mientras el enlace deba seguir funcionando. Para cambiar de rama hay que borrar la app y volver a crearla.

Para actualizar los datos del dashboard tras regenerar el pipeline:

```powershell
python -c "import pandas as pd; pd.read_csv('data/processed/covid_clean.csv').to_csv('data/dashboard/covid_clean.csv.gz', index=False, compression='gzip')"
```

Después se hace commit y push, y Streamlit redespliega solo.

## 5. Instalación

Necesitas Python 3.13 (probado con esa versión).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> **Nota para Windows con Smart App Control activado:** el bloqueo de binarios sin firma puede impedir que `pandas` cargue si está instalado `pyarrow` (lo instala Streamlit). Si te pasa, ejecuta `pip uninstall -y pyarrow`: pandas, los tests, el pipeline y el notebook funcionan sin él. Para el dashboard usa el enlace público o ejecútalo en un entorno sin esa restricción.

## 6. Cómo ejecutarlo

Todos los comandos, desde la raíz del repositorio y con el entorno activado.

**1. Pipeline completo (un solo comando)**

```powershell
python -m src.run_pipeline
```

Si no tienes el dataset en `data/raw/`, descárgalo antes:

```powershell
python -c "from src.run_pipeline import run_pipeline; run_pipeline(download=True)"
```

Para ejecutar solo la limpieza y las variables nuevas: `python -m src.run_processing` (acepta `--download`).

**2. Tests**

```powershell
python -m pytest -q
```

**3. Notebook**

```powershell
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=300 notebooks/02_eda_limpieza_y_analisis.ipynb
```

O ábrelo con `python -m jupyter lab`. Necesita que exista `data/raw/covid_us_states_daily.csv`. GitHub no muestra los gráficos interactivos de Plotly: ábrelo en Jupyter para verlos.

**4. Dashboard en local**

```powershell
python -m src.run_processing   # solo si aún no existe data/processed/covid_clean.csv
python -m streamlit run app.py
```

## 7. Estructura del repositorio

```
app.py                              Dashboard Streamlit
requirements.txt                    Dependencias con versiones fijadas
data/raw/                           Datos originales (ignorados por git)
data/external/                      Población 2019
data/processed/                     covid_clean.csv generado por el pipeline (ignorado por git)
data/dashboard/                     Copia comprimida de los datos procesados, para publicar el dashboard
notebooks/01_...                    Exploración inicial
notebooks/02_...                    EDA completo: limpieza, variables, gráficos, conclusiones
reports/informe_ejecutivo.pdf       Informe de 2 páginas para dirección
reports/guion_presentacion_5min.md  Guion de la presentación
reports/data_quality/               Informe de calidad de datos (.md y .json)
reports/initial_audit/              Auditoría inicial
reports/temporal_audit/             Auditoría temporal
reports/figures/                    Las 12 figuras del notebook
src/                                Código reutilizable
tests/                              95 tests con pytest
```

Módulos de `src/`:

| Módulo | Qué hace |
| --- | --- |
| `download_data.py` | Descarga el dataset |
| `audit_raw_data.py`, `analyze_missingness.py`, `analyze_state_coverage.py`, `analyze_data_quality.py`, `analyze_temporal_quality.py` | Las cinco auditorías (etapas 1 a 5) |
| `clean_data.py` | Limpieza reutilizable |
| `build_features.py` | Población, tasas por 100.000, medias de 7 días, letalidad, positividad, periodos y atípicos |
| `quality_report.py` | Informe de calidad de datos |
| `run_processing.py` | Encadena limpieza, variables nuevas y guardado |
| `run_pipeline.py` | Pipeline completo de 6 etapas |
| `dashboard_data.py` | Filtros y cifras del dashboard, sin Streamlit, para poder probarlos |

## 8. Problemas encontrados y cómo se resolvieron

| Problema | Solución |
| --- | --- |
| Incrementos negativos y valores imposibles en los datos | Se clipan a 0 y se marcan; los imposibles se marcan y no se borran |
| La positividad superaba el 100 % en 16 filas | Se anula solo en la variable derivada (`positivity_7d`) |
| Con menos de 4 estados, la agrupación por cuartiles de población fallaba | Se añadió un test que fallaba y una alternativa por rangos; el resultado con 51 estados no cambia |
| `data/processed/*.csv` está ignorado por git y el dashboard en la nube no tendría datos | Copia comprimida en `data/dashboard/` y búsqueda en dos rutas en `app.py` |
| En Windows, Smart App Control bloqueaba archivos compilados de `pyarrow` y `pandas` dejaba de cargar | `pip uninstall -y pyarrow` en local; el dashboard se ejecuta en la nube |
| Etiquetas de los gráficos que se solapaban | Se corrigieron en el notebook y se revisaron visualmente |
| Ramas encadenadas que daban errores de importación hasta mergear en orden | PR en orden: `data-audit`, `data-cleaning` y `dashboard-and-report` |

## 9. Limitaciones y trabajo futuro

- Cada estado cuenta las «pruebas» de forma distinta (28 cuentan pruebas virales, 14 «encuentros», 7 suman positivos y negativos y 2 cuentan personas), por lo que no se comparan pruebas entre estados.
- La letalidad es aparente (muertes entre casos confirmados) y depende de cuántas pruebas se hagan.
- Las relaciones entre variables se calculan con 51 puntos (uno por estado): sirven para plantear hipótesis, no para demostrar causas.
- Población de 2019, no de 2020.
- Los datos terminan el 7-mar-2021, antes de la vacunación masiva.
- Con más tiempo: añadir datos de vacunación y población más reciente, homogeneizar el conteo de pruebas entre estados y confirmar con cada estado los picos que parecen datos atrasados.

## 10. Tecnologías

Python 3.13, pandas, numpy, matplotlib, seaborn, plotly, Streamlit, pytest, Jupyter (`nbconvert`), Git y GitHub. Versiones exactas en `requirements.txt`.
