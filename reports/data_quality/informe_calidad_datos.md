# Informe de calidad de datos

Dataset: COVID Tracking Project, `states/daily` · 20.780 filas y 56 columnas de entrada · 56 jurisdicciones · 2020-01-13 a 2021-03-07.
Tras la limpieza: 20.780 filas y 32 columnas.

## Qué faltaba

Columnas conservadas con valores faltantes (% de filas vacías en el original):

| Columna | % vacío |
|---|---|
| totalTestsAntibody | 77.0 |
| negativeTestsViral | 75.8 |
| totalTestEncountersViral | 74.8 |
| deathProbable | 63.5 |
| positiveTestsViral | 56.9 |
| onVentilatorCurrently | 56.1 |
| totalTestsPeopleViral | 55.7 |
| probableCases | 55.4 |
| deathConfirmed | 54.7 |
| inIcuCurrently | 44.0 |
| recovered | 42.2 |
| hospitalizedCumulative | 40.4 |
| negative | 36.0 |
| positiveCasesViral | 31.4 |
| totalTestsViral | 30.1 |
| hospitalizedCurrently | 16.6 |
| death | 4.1 |
| positive | 0.9 |
| totalTestResults | 0.8 |

Además se descartaron 28 columnas (ver abajo). Los huecos de `positive` y `death` se concentran casi todos en las primeras semanas de 2020, antes de que cada estado empezara a reportar.

## Qué se corrigió

- **Duplicados:** 0 (la clave estado + fecha es única).
- **Tipo de dato:** `date` pasó de entero `YYYYMMDD` a fecha real.
- **Columnas descartadas**, agrupadas por motivo:

| Motivo | Columnas |
|---|---|
| Más de 80 % de valores faltantes: no es analizable | `pending` (89.7 % vacío), `inIcuCumulative` (81.8 % vacío), `onVentilatorCumulative` (93.8 % vacío), `hospitalizedDischarged` (85.2 % vacío), `positiveTestsAntibody` (83.9 % vacío), `negativeTestsAntibody` (93.0 % vacío), `totalTestsPeopleAntibody` (89.4 % vacío), `positiveTestsPeopleAntibody` (94.7 % vacío), `negativeTestsPeopleAntibody` (95.3 % vacío), `totalTestsPeopleAntigen` (95.2 % vacío), `positiveTestsPeopleAntigen` (97.0 % vacío), `totalTestsAntigen` (83.5 % vacío), `positiveTestsAntigen` (89.3 % vacío) |
| Metadato técnico de publicación (no describe la pandemia) | `lastUpdateEt` (3.0 % vacío), `dateModified` (3.0 % vacío), `checkTimeEt` (3.0 % vacío), `dateChecked` (3.0 % vacío), `hash` (0.0 % vacío) |
| Redundante: duplica o está obsoleta frente a otra columna | `hospitalized` (40.4 % vacío), `total` (0.0 % vacío), `posNeg` (0.0 % vacío) |
| Vacía o con un único valor: no aporta información | `dataQualityGrade` (100.0 % vacío), `commercialScore` (0.0 % vacío), `negativeRegularScore` (0.0 % vacío), `negativeScore` (0.0 % vacío), `positiveScore` (0.0 % vacío), `score` (0.0 % vacío), `grade` (100.0 % vacío) |

- **Huecos en acumulados:** relleno con el último valor conocido dentro de cada estado y, antes del primer reporte, con 0 (solo casos y muertes). Valores rellenados: `cases_cum` 188, `deaths_cum` 850, `tests_cum` 0.
- **Incrementos diarios negativos** (correcciones que hacen los estados): se dejaron en 0 y la fila quedó marcada en `correction_flag` (219 filas). Por columna: `new_cases` 24, `new_deaths` 73, `new_tests` 49, `new_hosp` 88.
- **Territorios** (AS, GU, MP, PR, VI): se marcan en `is_territory` para separarlos de los 50 estados + DC.

## Qué quedó pendiente y por qué

- **`tests_cum` sin valor al inicio** (166 filas): no se imputa con 0 porque un estado puede haber hecho pruebas antes de reportarlas; se deja vacío.
- **Ingresos hospitalarios actuales** (`hosp_now`, `icu_now`, `vent_now`): vacío significa "no reportado", no "cero"; imputar crearía una realidad que no está en la fuente.
- **Positivos > pruebas** en 59 filas: valor imposible (puede deberse a que casos y pruebas se miden en unidades distintas o con retraso). Se marcan en `cases_gt_tests`, no se corrigen porque no hay forma de saber cuál de las dos cifras está mal.
- **Unidades de las pruebas distintas por estado** (`tests_source`): unos cuentan personas, otros pruebas o encuentros. Por eso la positividad solo es aproximada y no debe compararse al milímetro entre estados.
- **Positividad imposible (> 100 %)** en 16 filas: en esa semana hay más casos nuevos que pruebas nuevas. En la variable derivada `positivity_7d` se convierten en vacío (NaN); las columnas originales no se tocan.
- **Picos diarios muy por encima de la media del estado**: probablemente cargas de datos atrasados o reclasificaciones (el dataset no lo confirma). Se conservan porque son valores de la fuente, se suavizan con medias de 7 días y se avisan en el análisis. Mayores saltos diarios de muertes en el original:

| Estado | Fecha | Muertes en un día |
|---|---|---|
| OH | 2021-02-12 | 2.559 |
| IN | 2021-02-04 | 1.546 |
| OH | 2021-02-13 | 1.204 |
| CA | 2021-02-25 | 1.114 |
| NY | 2020-05-07 | 951 |

- **Población (2ª fuente)** solo para los 50 estados + DC: los territorios no entran en los análisis por 100.000 habitantes.
- **Los datos terminan el 7 de marzo de 2021**: cualquier conclusión sobre el efecto de las vacunas o de olas posteriores queda fuera del alcance de este dataset.
