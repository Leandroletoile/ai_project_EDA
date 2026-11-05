# Guion de presentación · 5 minutos

**Hallazgo principal que queremos que se lleven:** *no hubo una pandemia, hubo tres olas; y para comparar olas y estados con justicia hay que mirar por habitante y con medias de 7 días.*

**Público:** una persona sin formación en datos. Sin siglas, sin código, una idea por bloque.
**Material:** 3 imágenes de `reports/figures/` (`08_tendencia_nacional.png`, `11_top_bottom.png`, `12_heatmap_estado_mes.png`) y, si hay tiempo, el panel interactivo abierto.
**Ritmo:** unas 600 palabras habladas a ritmo tranquilo. Dejan unos 40 segundos de pausas y cambio de imagen.

---

## 0:00 – 0:40 · Gancho y contexto

> Nos entregaron un archivo con más de veinte mil filas y cincuenta y seis columnas que nadie había mirado con calma. Nos pidieron tres cosas: datos limpios, datos con sentido y la historia que hay detrás. Esta es esa historia, en cinco minutos.

*Mostrar:* portada del informe (las cuatro cifras grandes).

## 0:40 – 1:50 · La historia 1: no fue una ola, fueron tres

> Si sumamos todos los estados día a día aparece algo que un promedio esconde: no hay una curva, hay tres.
> En primavera de 2020, un primer golpe fuerte: unos 31.000 casos al día en abril. Una pausa. En verano, una segunda ola de 66.000 casos al día a finales de julio.
> Y en invierno, el 11 de enero de 2021, **246.419 casos en un solo día**: casi cuatro veces el pico del verano. Ese invierno concentra tres de cada cuatro casos y seis de cada diez muertes de todo el periodo.
> Las muertes llegan unas semanas después: 3.334 al día el 13 de enero.

*Mostrar:* `08_tendencia_nacional.png`. Señalar con el dedo las tres jorobas.

## 1:50 – 3:00 · La historia 2: los totales engañan

> Primera pregunta de cualquier directivo: ¿qué estado lo pasó peor?
> Si miramos totales, la respuesta es California: 54.124 muertes, la cifra más alta del país. Pero California tiene casi cuarenta millones de habitantes.
> Si lo medimos por cada 100.000 habitantes, California queda en el puesto 29 de 51. El primero es **Nueva Jersey, con 265**. El último, Hawái, con 31.
> La lección práctica: comparar estados sin tener en cuenta su tamaño no compara la pandemia, compara tamaños.

*Mostrar:* `11_top_bottom.png`. Opcional: `12_heatmap_estado_mes.png` para ver que nueve estados, casi todos del noreste, tuvieron su peor mes en primavera y 42 de 51 lo tuvieron entre noviembre y febrero.

## 3:00 – 3:50 · La historia 3: una cifra tentadora

> Otra cifra que invita a sacar conclusiones es la letalidad: la proporción de casos que acaban en muerte. Entre primavera e invierno bajó de 4,4 % a 1,7 %. Suena a que se trató mejor.
> Pero cuidado: es una letalidad *aparente*. Dividimos muertes entre casos confirmados, y cuando se hacen más pruebas aparecen más casos leves, así que el divisor crece.
> Con estos datos no podemos afirmar por qué bajó. Y decirlo claramente también es parte de hacer bien nuestro trabajo.

## 3:50 – 4:35 · Cuánto fiarse de los datos

> Antes de confiar en ninguna cifra, limpiamos. Encontramos 219 registros con números negativos: son correcciones que hacen los propios estados. Y vimos que Ohio informó 4.484 muertes en tres días de febrero, el 6,3 % de todas las de ese mes en el país. No fue una explosión, fue un retraso al cargar datos.
> Por eso trabajamos con medias de siete días, marcamos todo lo que corregimos y dejamos documentado qué falta y por qué.

*Mostrar:* sección 4 del informe ejecutivo.

## 4:35 – 5:00 · Cierre

> Tres ideas para llevarse. Una: comparar siempre por habitante. Dos: leer los datos diarios con medias de siete días. Tres: no comparar pruebas entre estados hasta que todos las cuenten igual.
> Y para explorar por su cuenta, el panel interactivo: eligen estado, periodo e indicador. Gracias.

*Mostrar:* panel interactivo (pestaña *Evolución*).

---

## Preguntas que pueden hacer (y respuesta corta)

**¿Por qué no eliminaron los valores extremos?**
Entre el 7 % y el 11 % de los días son «atípicos» según la regla estadística, pero son los picos de las olas: justo lo que queremos ver. Solo los saltos que parecen carga atrasada (como Ohio) se avisan y se suavizan con la media de 7 días.

**¿Por qué rellenaron huecos con el último valor y con cero?**
Un total acumulado no baja: si hoy no se reportó, lo honesto es mantener el último. Antes del primer reporte el estado todavía no tenía casos ni muertes, así que es cero. Los ingresos hospitalarios *no* se rellenan: ahí un hueco significa «no reportado», no «cero».

**¿Por qué no hay relación entre pruebas y casos?**
Porque cada estado cuenta «prueba» de forma distinta: 28 cuentan pruebas virales, 14 «encuentros», 7 suman positivos y negativos y 2 cuentan personas. Es un resultado a tomar con cautela, no una prueba de que testear no sirva.

**¿Qué haría con más tiempo?**
Añadir datos de vacunación y de población más reciente, homogeneizar el conteo de pruebas entre estados y confirmar con cada estado los picos que parecen datos atrasados.

**¿Se puede decir que X causó Y?**
No. Las relaciones se calculan con 51 puntos (uno por estado) y sirven para plantear hipótesis, no para demostrar causas.
