# AI Log - Equipo UPITT Machine 

## Herramientas
- Gemini versión para estudiantes

## Filosofía de uso

Optamos usar herremientas de inteligencia artifial únicamente para tareas técnicas (selecciones de métodos e implementaciones), reservando el dominio del contexto a los integrantes del equipo, donde toda decisión que se requiera conocimiento acerca del entorno hidríco de México es responsablidad del equipo. 


## Registro de uso 

### 2026-03-30 | Gemini | Extracción de datos 
- **Tarea**: Le pedimos mínimo 3 opciones para extraer datos históricos de la Comisión Nacional del Agua en México.
- **Prompt**: "Dame 3 opciones mínimo para poder extraer datos históricos del monitoreo de presas de la Comisión Nacional del Agua (CONAGUA) en México, para cada opción menciona las librerías de Python sugeridas y la implementación de cada una"
- **Resultado**: Nos proporciono 3 maneras técnicas con API REST/Servicios Web, descarga de datasets y Web Scraping del SIPEb.
- **Decisión**: Se eligió realizar la extracción con API REST JSON debido a la capacidad de poder recuperar datos históricos de manera estructurada. 


### 2026-03-30 | Gemini | Extracción de fechas 
- **Tarea**:Establecer un rango de fechas para le extracción de los datos.
- **Prompt**: "Cómo puedo extraer datos hídricos estableciendo un rango de fechas (fecha_inicio y fecha_fin) haciendo uso de la librería datetime de Python"
- **Resultado**: Nos dio la forma de hacerlo haciendo uso de la librería datetime y otra opción pero haciendo uso de la librería de Pandas para la tarea.
- **Decisión**: Elegimos la implementación de datetime porque presenta una forma más clara de poder extraer las fechas, además establecimos un parámetro anio_inicio que recibe la función. 

### 2026-03-30 | Gemini | Manejo de Archivos
- **Tarea**:Implementar un mecanismo de limpieza de archivos locales.
- **Prompt**: "Genera un fragmento de código en Python que verifique si un archivo de salida ya existe dentro de una ruta específica y lo elimine para evitar duplicados"
- **Resultado**: Nos proporcionó una manera donde se trata las rutas como obejtos con la librería de pathlib y otra usando os que es una forma más tradicional.
- **Decisión**: Optamos por utilizar os ya que solo necesitabamos una manera sencilla de implemetar la tarea sin entrar mucho a detalle en cuanto a la estructura de objetos. 

### 2026-03-30 | Gemini | Manejo de Excepciones y Seguridad SSL
- **Tarea**:Implementar la solicitud de datos al servidor de CONAGUA gestionando posibles fallos de conexión.
- **Prompt**: "En una linea de codigo como podemos consultar una API utilizando la libería Requests de Python, que la petición se incluya un tiempo de espera y una forma de evitar errores de conexión con los servidores gubernamentales. Este va a estar contenido en una estructura try."
- **Resultado**: La implementación de petición HTTP y nos sugirió hacer uso del parámetro verify = false para manejar el error del certificado SSL vencido.
- **Decisión**: Optamos por hacer uso del parámetro para garantizar la continuidad de la extracción de los datos sin interrupciones.

### 2026-03-31 | Gemini | Optimización de Almacenamiento de Datos
- **Tarea**:Seleccionar e implementar el formato de almacenamiento más eficiente para el dataset histórico del monitoreo de presas.
- **Prompt**: "Utlizando Pandas sugiere formas 3 formas de almacenar un dataset de series de tiempo comparando velocidad y peso."
- **Resultado**: Proporciona formatos como CSV y Parquet donde se destaca Parquet por su almacenamiento y eficiencia en memoria.
- **Decisión**: Se optó por la implementación de Parquet para el manejo de los datos históricos usando ruta_salida, debido a que un archivo CSV se volvería demasiado pesado.


### 2026-03-31 | Gemini | Configuración de Rutas 
- **Tarea**:Definir la arquitectura de rutas locales y los puntos de enlace (endpoints) de la API para una correcta localización de los recursos.
- **Prompt**: "Define en Python las variables de configuración para un proyecto de extracción de datos. Sugiere una ruta relativa para guardar archivos en formato Parquet dentro de una carpeta de datos."
- **Resultado**: Propociono las constantes ruta_maestra utilizando rutas relativas (../datos/...).
- **Decisión**: Se decidió utilizar rutas relativas en lugar de rutas absolutas (como C:\Usuarios\...) para asegurar que el repositorio sea completamente portable entre los miembros del equipo.


### 2026-03-31 | Gemini | Detección de Vacíos
- **Tarea**: Identificar inconsistencias o registros faltantes (huecos temporales) en el dataset extraído para garantizar la continuidad de la serie de tiempo.
- **Prompt**: "Utilizando la librería Pandas, explica cómo encontrar las fechas faltantes en un índice de tiempo. Supón que tengo un calendario_ideal con todas las fechas que deberían existir y un conjunto de dias_existentes extraídos de un archivo.
- **Resultado**: Para detectar resgistros faltantes en series temporales de datos hídricos, el enfoque más eficiente en Pandas es utilizar el método .difference().
- **Decisión**: Se decidió calcular los huecos de información con el método sugerido antes de proceder con el análisis para decidir como tratarlos.


### 2026-04-1 | Gemini | Normalización de identificadores
- **Tarea**:Estandarizar números de estación mediante padding para asegurar una longitud uniforme.
- **Prompt**: "Escribe una función en Python que use zfill() para convertir un entero a string con ceros a la izquierda, explicando su utilidad en identificadores compuestos"
- **Resultado**: Implementación de .zfill() que transforma enteros en cadenas de longitud fija.
- **Decisión**: Se aplicó la implementación de .zfill(3) para cumplir con los requerimientos de la API de CONAGUA, evitando errores de formatos incorrectos.


### 2026-04-1 | Gemini | Detección de faltantes
- **Tarea**:Identificar días sin registro mediante el cruce con un calendario maestro.
- **Prompt**: "Usa Pandas para hacer un left merge entre un DataFrame de CALENDARIO_IDEAL y df_periodo por la columna 'fechamonitoreo' para exponer nulos."
- **Resultado**: Código con la implementación de pd.merge(..., how='left') que integra todas las fechas teóricas, marcando las ausentes con NaN.
- **Decisión**: Se utilizó por left merge con el fin de garantizar la continuidad de la serie de tiempo.


### 2026-04-2 | Gemini | Imputación Avanzada de Datos
- **Tarea**: Rellenar valores faltantes (NaN) en el dataset de presas utilizando técnicas de regresión para mantener la consistencia estadística..
- **Prompt**: "Utilizando scikit-learn, sugiere un método de imputación multivariado más avanzado que la media, proporciona el código para aplicar sobre columnas específicas de un DataFrame."
- **Resultado**: Sugiere el método de imputación IterativeImputer. 
- **Decisión**: Se eligió IterativeImputer en lugar de una imputación simple (media/mediana) porque los niveles de las presas están correlacionados. Este método preserva mejor la relación entre variables.


### 2026-04-3 | Gemini | Conversión de Formatos (CSV a Parquet)
- **Tarea**: Automatizar la conversión de formato CSV a Parquet para optimizar el rendimiento del proyecto.
- **Prompt**: "Usa Pandas para convertir archivos CSV a Parquet de forma eficiente. El código debe leer el CSV con low_memory=False, generar el nombre de salida reemplazando la extensión y guardar el resultado sin índices"
- **Resultado**: Código con la conversión que utiliza pd.read_csv() seguido de df.to_parquet(). 
- **Decisión**: Se decidió crear un conversor en un archivo separado de la lógica principal, permitiendo una transición rápida de archivos.


### 2026-04-5 | Gemini | Gestión de Alertas del Sistema
- **Tarea**: Desactivar notificaciones no críticas del sistema y librerías para optimizar la legibilidad de la consola.
- **Prompt**: "Escribe el código necesario para ignorar todas las advertencias generadas durante la ejecución del script, con el fin de mantener una consola más limpia y enfocada solo en los resultados."
- **Resultado**: Sugerencia de la implementación de warnings.filterwarnings('ignore').
- **Decisión**: Se optó por silenciar las advertencias para mejorar la experiencia de usuario en la consola y el dashboard..
