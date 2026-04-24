# 💧 UPIIT Machine 

**Integrantes:**
1. Elisa Naomi Alvarado Sanchez
2. Ricardo Polock Suarez Geovani
3. Bryan Hernández Alvarez 

Bienvenido al repositorio oficial del proyecto **"¿Cuáles son las presas mexicanas más vulnerables y cómo podemos anticipar su agotamiento?"** desarrollado por el equipo UPIIT Machine para el HackODS UNAM 2026. 

Este proyecto es un tablero interactivo que basa parte de sus contenidos en Inteligencia Artificial diseñada desde cero por el equipo, para visibilizar, analizar y anticipar el nivel de estrés hídrico y riesgo de desabasto en las presas de México frente a diversos escenarios de cambio climático.

---

## 🌎 Alineación con los Objetivos de Desarrollo Sostenible (ODS)

Este proyecto busca abordar la crisis hídrica de frente, aportando herramientas de toma de decisión fundamentadas en datos comprobables.

* **Pregunta o problema central:** Este producto tiene como objetivo resaltar la vulnerabilidad de las presas mexicanas ante el cambio climático y el riesgo de desabasto de agua, incluyendo un componente predictivo, generando una herramienta de prevención. La pregunta es: **"¿Cuáles son las presas mexicanas más vulnerables y cómo podemos anticipar su agotamiento?"**.
* **Pertinencia con el ODS:** Este proyecto impacta directamente en el **ODS 6: Garantizar la disponibilidad y la gestión sostenible del agua y el saneamiento para todos**, ya que monitorea históricamente e identifica de manera predictiva el nivel hídrico de todo México.
* **Coherencia narrativa:** Nuestra historia sigue la siguiente línea, dividida en secciones del tablero:
  1. Con ayuda de algunas estadísticas, mostramos el nivel actual de las presas en México.
  2. Generamos un suavizado para identificar la tendencia histórica de los niveles hídricos.
  3. Apoyándose de una animación nacional, se establece una línea temporal de la situación desde 1995 a 2025.
  4. Finalmente, se hace una sección especial para la actualidad (al menos hasta donde se reporta), partiendo la historia, hasta aquí se da un contexto con datos.
  5. Empezamos con la sección que predice distintos escenarios; en primera instancia, qué pasaría con aumentos de temperatura.
  6. Después, se muestra una proyección de lo que sería la tendencia debido al comportamiento histórico.
  7. Para terminar, mostramos un filtrado de todos los elementos posibles, que podrían generar una toma de acción para prevención por parte del público al que va dirigido nuestro trabajo. Algunos perfiles que se consideran:
     * CONAGUA, protección civil, gobierno estatal y/o federal.
     * Sector agrícola.
     * Planeadores urbanos.
     * ONGs y activismo ambiental.
* **Potencial de impacto:** Hace visible un problema de todo el mundo acotado solo a México y sus presas. Al tener en cuenta datos históricos, climáticos y predicciones a partir de lo anterior, se pueden tomar decisiones informadas para garantizar la disponibilidad y gestión sostenible del agua.

---

## 🗓️ Desarrollo del Proyecto (Cronología)

A continuación, explicamos todo el proceso desde la recolección de datos:

### 1. Fase 1: Recolección y Extracción de Datos (Web Scraping)
* **Tiempo de ejecución:** 7.03 horas

- *Extracción de datos CONAGUA*
A partir del endpoint público `https://sinav30.conagua.gob.mx:8080/PresasPG/presas/reporte/{YYYY-MM-DD}` se extrajeron los datos históricos de las 210 presas de México desde el año 1995 hasta abril de 2025. Atrapamos las respuestas estructuradas en JSON iterando día a día. Se agruparon las peticiones por lotes y guardamos en formato Parquet.
En un principio se hacía en formato csv, pero para evitar problemas con github, se hizo una conversión.

- *Construcción del Data Lake de estaciones climáticas en México*
Identificamos que cuando pedimos datos históricos de las estaciones climáticas en todo el país de México en el Sistema Metereológico Nacional (SMN), los reportes eran lanzados bajos direcciones estáticas en forma de TXT, entonces en lugar de abrirlos en navegador, los capturamos en nuestro entorno local, el patrón URL es:
`(https://smn.conagua.gob.mx/tools/RESOURCES/Normales_Climatologicas/Diarios/{carpeta_estado}/dia{id_estacion}.txt)`

  1. Hicimos uso de fuerza bruta puesto que no sabíamos cuántas estaciones había por estado (solamente que existen más de 5000 pero solo 2800 están en funcionamiento), mapeamos los 32 códigos que provee el INEGI y generamos 32,000 combinaciones de URL posibles.
  2. Así, hicimos un escaneo multi hilo, lanzando 30 *workers* en paralelo para los directorios.
  3. Cada vez que se obtenía un código de respuesta 200, leíamos el encabezado del TXT para verificar la existencia de latitud y longitud para proceder a la descarga en un subdirectorio en `/datos`.

### 2. Fase 2: Cruce Espacial y Red Hídrica
* **Tiempo de ejecución:** 20 minutos

Una vez obtenido los datos anteriores, procedimos a hacer un cruce de los mismos, para tener más contexto entre el llenado que reporta CONAGUA de las presas y las condiciones del clima del SMN.

- *Cálculo de la Estación Más Cercana* Desarrollamos una función vectorizada por numpy, que toma la longitud y latitud de cada presa y calcula la distancia euclidiana contra el catálogo de estaciones climatológicas del país.

$$d = \sqrt{(lat_{presa} - lat_{estacion})^2 + (lon_{presa} - lon_{estacion})^2}$$

- *Datos de Estación Óptimos para cada Presa* No nos limitamos a buscar solo la estación más cercana, pues se filtraban las *Top 5* estaciones más próximas a la presa y se evaluaba el historial entre 1995-2025. Se seleccionó la estación con mejor calidad de datos, tomando en cuenta la menor cantidad de valores nulos para los registros de lluvia, temperatura y evaporación.

- *Orquestación Multi-Proceso*
Dadas las muchas combinaciones por el proceso explicado, se agruparon las presas únicas y se procesaron en paralelo con todos los núcleos disponibles en un procesador intel i5 9600K, para obtener el primer dataset con datos climáticos y de presas `dataset_bruto_total.parquet`.

### 3. Fase 3: Limpieza y Curación de Datos
* **Tiempo de ejecución:** 5 minutos

La información obtenida por lo general es ruidosa estadísticamente, desordenada e incompleta. Para garantizar el entrenamiento que teníamos previsto para nuestro modelo predictivo, limpiamos, rellenamos y estandarizamos los datos.

- *Imputación Doble de Valores Nulos*
  1. Primero, agrupando por presa, se aplicó una *interpolación lineal bidireccional*:
  $$y = y_0 + \frac{(y_1 - y_0)}{(t_1 - t_0)} (t - t_0)$$
  Dónde $y$ es el valor a imputar, $t$ es el punto en el tiempo dónde falta el dato, $y_0$ es el último valor existente, $t_0$ es el tiempo del último valor existente, $y_1$ es el siguiente valor existente y $t_1$ es el tiempo del primer valor existente.
  2. Utilizamos el método *Iterative Imputer de scikit-learn* para imputar probabilísticamente los huecos más grandes.

- *Detección de Valores Atípicos*
Nuevamente al agrupar por presa, calculamos el Z-Score a los reportes de volumen y nivel hídrico:
$$Z = \frac{x - \mu}{\sigma}$$
Dónde $Z$ es la puntuación, $x$ el valor individual, $\mu$ la media y $\sigma$ la desviación estándar.
Para que todo aquel registro que representara una desviación estándar absoluta mayor o igual a 3 ($Z \ge 3$) fuera considerado un valor atípico y eliminado.

- *Escalado Min-Max*
Finalmente, para evitar problemas de convergencia, se normalizaron las escalas entre 0 y 1.

Todo el proceso anterior, nos da como resultado el dataset `dataset_limpio_modelo.parquet` en `/datos`.

### 4. Fase 4: Entrenamiento de Modelo Profundo
* **Tiempo de ejecución:** 1.5 horas

Una vez con todos los datos limpios, decidimos utilizar además de estadísticos y series de tiempo tradicionales, valores de predicción. Enseñando la historia hídrica-climática a un modelo de *Machine Learning* para obtener lo que necesitamos para mostrar en nuestro Tablero.

- *Arquitectura de la Red (Transformer Regresor)*
Diseñamos desde cero una arquitectura de red profunda basada en Transformers (el mismo tipo de algoritmo que dio paso a modelos grandes de lenguaje como ChatGPT, pero adaptado a regresiones numéricas continuas).
  1. ¿Por qué usamos esta arquitectura? Mientras otros modelos recurrentes no consideran más contexto en los datos, el Transformer, gracias a su mecanismo de Autoatención es capaz de correlacionar toda la porción de datos que se le muestre.
  2. Implementamos a nivel técnico proyección de Embeddings, un codificador posicional temporal para que la red comprendiera que el tiempo es secuencial, seguido de 2 módulos con 4 cabezas de atención cada uno.

- *Entradas y Salidas*
  1. *Entrada*: El modelo recibe una serie de datos en forma de ventanas deslizantes, se le pasan 10 días continuos con 7 variables: latitud, longitud, precipitación, evaporación, temperatura máxima, volumen y nivel hídrico.
  2. *Salida*: El modelo predice el nivel hídrico y el volumen para el siguiente día.
  3. El propósito es lograr alterar entradas de parámetros y ver qué sucede si, por ejemplo, aumenta la temperatura hasta 3 grados Celsius.

- *Éxito del Modelo Predictivo*
  1. **Coeficiente de Determinación ($R^2$ Score): 0.9265**
  Demuestra que el modelo simuló exitosamente el 92.65% del comportamiento histórico, garantizando que el tablero no genera "alucinaciones" sino proyecciones basadas en datos observables. 
  $$R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$
  2. **Error Absoluto Medio (MAE): 0.0006**
  Garantiza una inferencia casi perfecta, al confirmar matemáticamente que nuestro algoritmo falla en promedio apenas un 0.06% respecto al nivel hídrico real medido físicamente en la presa. 
  $$MAE = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$
  3. **Error Cuadrático Medio (MSE): 0.0001**
  Penaliza severamente los errores grandes; al tener un valor tan diminuto, nos asegura que el modelo está balanceado y nunca generará gráficos con predicciones ilógicas o grandes picos. 
  $$MSE = \frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2$$
  4. **Raíz del Error Cuadrático Medio (RMSE): 0.0015**
  Comprueba estadísticamente la dispersión, verificando que la variación del modelo se acota a $0.0015$ unidades consolidadas. 
  $$RMSE = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$$

Con $n$: Cantidad total de observaciones, $y_i$: El nivel hídrico real reportado, $\hat{y}_i$: Inferencia, $\bar{y}$: La media global.

Con todo lo anterior generamos el dataset final a presentar `predicciones_finales_smn.csv` en `/datos`.

### 5. Fase 5: Construcción del Tablero de Decisión
A través de las tecnologías de Quarto y Plotly, generamos nuestro tablero con las visualizaciones:

- *Tarjetas KPI y Nube de Palabras*
Muestran la situación actual, utilizamos `dataset_limpio_modelo.parquet`, que empareja con predicciones del modelo y diccionarios de frecuencia de texto.

- *Gráfica de Tendencia Histórica*
Serie de tiempo que suaviza los últimos 30 años de almacenamiento en presas. Los datos utilizados fueron el `nivel_hidrico_pct` filtrado por fecha.

- *Animación Nacional*
Un mapa de dispersión con un slider temporal que muestra la evolución del nivel hídrico en las presas de México.

- *Mapa en la Actualidad*
Visualización similar a la anterior, pero está solamente reportando el último día en nuestros datos.

- *Escenarios Térmicos, Vulnerabilidad y Matriz de Toma de Decisiones*
Mapas dinámicos que muestran y permiten manipular distintos niveles de temperatura, para visualizar las afectaciones.
Filtrado de presas que tienen alto riesgo de quedarse vacías.

---

## 📊 Metadatos de los Datos Utilizados

* **Justificación de la selección:** Elegimos estos conjuntos de datos porque representan la correlación de nuestro problema: el comportamiento de captación e infraestructura hídrica real cruzado contra el impacto de las variables climáticas. Y que aportan a nuestro ODS elegido. En palabras de CONAGUA, las presas son estructuras que permiten almacenar y retener agua para el consumo humano, el riego agrícola, generación de electricidad y más. [Enlace de referencia](https://www.facebook.com/photo.php?fbid=983105527332216&set=a.297332789242830&id=100068983324521)
* **Verificabilidad de la fuente:** Todos los registros en este proyecto provienen únicamente de fuentes públicas, verificables y confiables pertenecientes al Gobierno de México. Las fuentes son: **CONAGUA** (Comisión Nacional del Agua) vía el Sistema Nacional de Información del Agua (SINA) y el **SMN** (Servicio Meteorológico Nacional).
Captados del [SINA](https://sinav30.conagua.gob.mx:8080/Presas/) para el monitoreo de Presas y del [SMN](https://smn.conagua.gob.mx/es/climatologia/informacion-climatologica/informacion-estadistica-climatologica) para la información estadística climatológica.
Además de los datos provenientes del modelo predictivo que es reproducible a partir del script `3_0_EntrenamientoModeloUPIITMACHINE.py` en `/scripts`.
* **Licencia:** Datos Abiertos del Gobierno de la República (Open Data), de libre uso citando la fuente.
* **Fecha de Descarga:** Extracción dinámica abarcando del **1 de enero de 1995 al 1 de abril de 2025**.

### Descripción de Datasets y Variables

#### 1. Dataset de Presas Históricas (`historico_presas_conagua_api.parquet`)
Contiene el reporte histórico diario del estado físico e hídrico de todas las presas registradas.
* `fecha`: Fecha en la que se realizó la toma o el reporte hídrico.
* `clavesih`: Clave maestra de identificación en el sistema.
* `latitud` / `longitud`: Coordenadas geográficas.
* `nivel_hidrico_pct` (Lleno al %): Porcentaje actual (0 a 100) en relación a su capacidad.
* `volumen_hm3`: Volumen absoluto de agua almacenada medido en hectómetros cúbicos.

#### 2. Catálogo de Estaciones y Variables Climáticas (`estaciones_climatologicas.csv` y TXTs extraídos del SMN)
Base meteorológica de las estaciones en todo el país.
* `lluvia_mm`: Cantidad de precipitación registrada.
* `evaporacion_mm`: Tasa de evaporación del agua.
* `temp_max_c`: Temperatura máxima del día registrada en la región en °C.
* `temp_min_c`: Temperatura mínima del día.

#### 3. Dataset Maestro Limpio (`dataset_limpio_modelo.parquet`)
Es la consolidación limpia orientada al entrenamiento de nuestro modelo de aprendizaje. Adicionalmente todas las variables climáticas e hídricas mencionadas anteriormente procesadas por imputación múltiple y *Min-Max scaling* (valores entre 0.0 y 1.0 para el modelo predictivo). 

#### 4. Predicciones Finales de la IA (`predicciones_finales_smn.csv`)
Archivo maestro de predicciones del modelo predictivo, listo para su representación final en el tablero.
* `pred_pct_Base`: Posición real o histórica calculada (tendencia a futuro base).
* `pred_pct_Temp_+1C`: Proyección del porcentaje de reservorio si la anomalía térmica global sube 1°C.
* `pred_pct_Temp_+2C`: Proyección del porcentaje de reservorio si el clima sube 2°C.
* `pred_pct_Temp_+3C`: Escenario catastrófico de desecación si la temperatura aumenta 3°C global.

---

### Notas:
1. El proyecto se limita a que las proyecciones por aumento de temperatura son simuladas; sin embargo, el modelo está listo para calcular estas predicciones. Por cuestiones de tiempo se acotó el alcance.
2. Dado que la rúbrica de corte no menciona la existencia obligatoria de libretas de Jupyter, las visualizaciones se encuentran en el archivo `.qmd` alojado en `/dashboard`. Además, por cuestiones de tiempo, no fue posible migrar los archivos en `/scripts` a libretas de Jupyter, sin embargo, son ejecutables y los resultados reproducibles en cualquier entorno de Python bajo las dependencias descritas en `pyproject.toml`.
3. Nuestro primer archivo de Declaración de IA fue corrompido, intentamos reconstruirlo, por lo que consideramos que es carente de algunas secciones; sin embargo, el uso de modelos grandes de lenguaje está acotado al uso estratégico, un acelerador, mas no un sustituto.
4. Hacemos énfasis en que el proceso de web scraping se hizo directamente a archivos estructurados que las instituciones proveen como DATOS ABIERTOS en distintos formatos y que no fue hecho para extraer contenido en páginas HTML o parecidos.

---
*Hecho por el equipo UPIIT Machine.*