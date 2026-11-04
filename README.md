# EDA COVID-19: análisis de la pandemia en Estados Unidos

Proyecto de análisis exploratorio de datos (EDA) y auditoría de calidad de datos desarrollado durante la formación en AI Engineering de Factoría F5.

El proyecto analiza la evolución de la pandemia de COVID-19 en Estados Unidos mediante datos históricos del COVID Tracking Project, aplicando técnicas de análisis exploratorio, análisis temporal y validación de consistencia.

## Objetivos

- Explorar la evolución temporal de la pandemia.
- Analizar la disponibilidad y calidad de los datos.
- Comparar la cobertura entre estados y territorios.
- Identificar valores negativos, anomalías y posibles inconsistencias.
- Evaluar la coherencia entre incrementos diarios y valores acumulados.
- Generar informes reproducibles mediante un pipeline automatizado.

## Fuente de datos

**COVID Tracking Project**

Fuente original: https://api.covidtracking.com/v1/states/daily.json

Dataset utilizado: `covid_us_states_daily.csv`

- Registros: 20.780
- Columnas: 56
- Período analizado: 13 de enero de 2020 – 7 de marzo de 2021.
- Jurisdicciones de referencia: 56.

El conjunto incluye estados, Washington D. C. y territorios estadounidenses. Por este motivo, se utiliza el término *jurisdicciones* en lugar de estados cuando se describe la cobertura territorial.

## Tecnologías

- Python
- Pandas
- NumPy
- Matplotlib
- Seaborn
- JupyterLab
- Requests
- Pytest

## Estructura del proyecto

```text
proyecto_eda_covid/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── notebooks/
│   └── 01_exploratory_data_analysis.ipynb
│
├── reports/
│   ├── figures/
│   ├── initial_audit/
│   └── temporal_audit/
│
├── src/
│   ├── download_data.py
│   ├── audit_raw_data.py
│   ├── analyze_missingness.py
│   ├── analyze_state_coverage.py
│   ├── analyze_data_quality.py
│   ├── analyze_temporal_quality.py
│   └── run_pipeline.py
│
├── tests/
│
├── requirements.txt
├── .gitignore
└── README.md
```

## Pipeline de análisis

El proyecto dispone de un pipeline automatizado que ejecuta cinco etapas:

### 1. Auditoría inicial

Analiza la estructura del dataset, los tipos de datos, los valores faltantes, los registros duplicados y las estadísticas descriptivas.

Genera informes de estructura, estadísticas, disponibilidad y cobertura.

### 2. Análisis de valores faltantes

Examina la disponibilidad de información y cuantifica los valores ausentes en las variables del dataset.

### 3. Cobertura de jurisdicciones

Analiza la distribución territorial y la evolución de la disponibilidad de registros.

### 4. Auditoría de calidad de datos

Identifica:
- Valores negativos en variables de incrementos diarios.
- Columnas constantes.
- Columnas completamente vacías.
- Distribución de anomalías por jurisdicción.

### 5. Auditoría de calidad temporal

Examina:
- Registros duplicados.
- Saltos en el calendario.
- Descensos en valores acumulados.
- Valores diarios extremos.
- Consistencia aritmética entre incrementos diarios y valores acumulados.
- Cobertura temporal de las jurisdicciones.

## Resultados principales

### Calidad de los datos

Se analizaron 20.780 registros y 56 columnas.

Se identificaron 304 valores negativos distribuidos entre cinco variables:

| Variable | Valores negativos |
|---|---:|
| positiveIncrease | 24 |
| negativeIncrease | 70 |
| totalTestResultsIncrease | 49 |
| deathIncrease | 73 |
| hospitalizedIncrease | 88 |
| **Total** | **304** |

También se identificaron:
- 5 columnas constantes.
- 2 columnas completamente vacías.

### Auditoría temporal

Los principales resultados fueron:

| Indicador | Resultado |
|---|---:|
| Registros duplicados | 0 |
| Intervalos con saltos de fechas | 0 |
| Días ausentes del calendario | 0 |
| Descensos en valores acumulados | 230 |
| Valores diarios extremos | 660 |

Los valores extremos son señales estadísticas que requieren investigación contextual y no representan necesariamente errores.

### Consistencia entre incrementos diarios y acumulados

Se realizaron 60.968 comparaciones aritméticas entre incrementos diarios y valores acumulados.

| Variable | Comparaciones coincidentes |
|---|---:|
| positiveIncrease vs positive | 20.536 / 20.536 |
| deathIncrease vs death | 19.874 / 19.874 |
| totalTestResultsIncrease vs totalTestResults | 20.558 / 20.558 |
| **Total** | **60.968 / 60.968** |

No se detectaron discrepancias aritméticas en estas comparaciones.

Esta consistencia no demuestra por sí sola la exactitud epidemiológica de los datos.

### Cobertura de jurisdicciones

Se analizaron 420 días de calendario y 56 jurisdicciones de referencia.

- Días con cobertura completa: 357.
- Días con cobertura parcial: 63.
- Primer día con cobertura completa: 16/03/2020.
- Último día con cobertura completa: 07/03/2021.

La cobertura completa se mantuvo durante un único período continuo de 357 días.

La cobertura completa significa que las 56 jurisdicciones disponen de registros para una fecha determinada. No implica que todas las variables de esos registros estén completas.

## Informes generados

Los resultados se guardan en formato CSV y TXT.

**reports/initial_audit/**
- `audit_summary.txt`
- `data_types.csv`
- `missing_values.csv`
- `monthly_data_availability.csv`
- `numeric_statistics.csv`
- `state_coverage.csv`
- `temporal_coverage.csv`
- `negative_values.csv`
- `negative_values_by_state.csv`
- `constant_columns.csv`
- `data_quality_summary.txt`

**reports/temporal_audit/**
- `temporal_quality_summary.txt`
- `duplicate_records.csv`
- `date_gaps.csv`
- `cumulative_decreases.csv`
- `extreme_values.csv`
- `daily_cumulative_consistency_details.csv`
- `cumulative_daily_consistency.csv`
- `cumulative_daily_mismatches.csv`
- `jurisdiction_coverage.csv`
- `jurisdiction_coverage_summary.txt`

## Instalación

Clonar el repositorio:

```bash
git clone <URL_DEL_REPOSITORIO>
cd proyecto_eda_covid
```

Crear un entorno virtual:

```bash
python -m venv .venv
```

Activarlo en Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Descargar los datos

El dataset original no se incluye en Git.

Para descargarlo desde la API:

```bash
python -m src.download_data
```

También se puede ejecutar el pipeline solicitando previamente la descarga desde el propio código:

```python
from src.run_pipeline import run_pipeline

run_pipeline(download=True)
```

## Ejecutar el análisis

Con el dataset disponible en `data/raw/covid_us_states_daily.csv`:

```bash
python -m src.run_pipeline
```

Los informes se generarán automáticamente en el directorio `reports/`.

## Ejecutar los tests

```bash
python -m pytest -v
```

## Notebook exploratorio

El análisis exploratorio complementario está disponible en:

`notebooks/01_exploratory_data_analysis.ipynb`

Para abrirlo:

```bash
jupyter lab
```

## Consideraciones metodológicas

- Los datos originales se conservan sin modificaciones ni eliminaciones durante las auditorías.
- Los valores negativos pueden responder a revisiones retrospectivas de los registros.
- Los valores extremos requieren interpretación contextual.
- Los descensos en valores acumulados no deben clasificarse automáticamente como errores.
- La consistencia aritmética no garantiza la exactitud epidemiológica.
- La cobertura territorial y la disponibilidad de variables son dimensiones diferentes de la calidad de datos.

## Estado del proyecto

Proyecto de análisis exploratorio y auditoría de calidad de datos desarrollado como parte de la formación en AI Engineering de Factoría F5.
