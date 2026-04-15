#Hacemos la importación de las librerías necesarias
import os
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
import urllib3
from tqdm import tqdm

# Desactivamos advertencias de certificados de seguridad del gobierno
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#Definimos la función para extraer los datos del monitoreo de Presas de la CONAGUA
#anio_inicio: año de inicio, delay_minimo: delay minimo, delay_maximo: delay maximo, tamano_lote: tamaño del lote para guardado
def extraer_historico_api_json(anio_inicio=1995, delay_minimo=0.5, delay_maximo=1.5, tamano_lote=50):
    print("Iniciando extracción masiva vía API REST JSON (1995 - Actualidad)...")
    #Se define el tiempo de inicio para medición
    start_time = time.time()
    
    # Colocamos la URL base dónde se capturan los archivos JSON del monitoreo histórico de presas
    URL_BASE = "https://sinav30.conagua.gob.mx:8080/PresasPG/presas/reporte/"
    
    #Establecemos el rango de fechas para la extracción de datos
    fecha_inicio = datetime(anio_inicio, 1, 1)
    fecha_fin = datetime.now()
    dias_totales = (fecha_fin - fecha_inicio).days
    
    # Colocamos la ruta de salida de los archivos tabulares a parquet
    os.makedirs('../datos', exist_ok=True)
    ruta_salida = '../datos/historico_presas_conagua_api.parquet'
    
    # Si existe un archivo de una prueba anterior, lo limpiamos para empezar fresco
    if os.path.exists(ruta_salida):
        os.remove(ruta_salida)
        
    session = requests.Session()
    # Le decimos al servidor que específicamente queremos la respuesta en JSON
    session.headers.update({
        #Tenemos que simular un navegador para que el servidor no nos bloquee
        #User-Agent: Identificador del navegador
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        #Accept: Tipo de respuesta que queremos
        'Accept': 'application/json'
    })

    #Listas para almacenar los datos
    lote_actual = []
    dias_fallidos = []
    registros_totales_guardados = 0
    df_total = pd.DataFrame()
    #Iteramos sobre el rango de fechas para extraer los datos 
    for i in tqdm(range(dias_totales), desc="Extrayendo JSONs diarios...", unit="día"):
        #Definimos la fecha actual
        fecha_actual = fecha_inicio + timedelta(days=i)
        #Definimos la fecha actual en formato string
        fecha_str = fecha_actual.strftime('%Y-%m-%d')
        #Definimos la URL de la API
        url_api = URL_BASE + fecha_str

        try:
            # verify=False nos salva del error del certificado SSL vencido
            response = session.get(url_api, timeout=15, verify=False)
            
            if response.status_code == 200:
                #Convertimos la respuesta a JSON
                datos_json = response.json()
                
                # Si el servidor responde con datos (a veces hay días vacíos "[]")
                if datos_json: 
                    # Pandas convierte el JSON a un DataFrame
                    df_dia = pd.DataFrame(datos_json)
                    lote_actual.append(df_dia)
            else:
                dias_fallidos.append(fecha_str)

        except Exception as e:
            dias_fallidos.append(fecha_str)
            
        # Finalmente hacemos un guardado por lotes
        if len(lote_actual) >= tamano_lote or i == (dias_totales - 1):
            if lote_actual:
                # Unimos los últimos 50 días
                df_lote = pd.concat(lote_actual, ignore_index=True)
                
                # Acumulamos en el df total
                df_total = pd.concat([df_total, df_lote], ignore_index=True)
                
                registros_totales_guardados += len(df_lote)
                lote_actual = [] # Vaciamos la memoria RAM
                
        # Aquí es dónde hacemos uso del delay para evitar el bloqueo del sitio
        time.sleep(random.uniform(delay_minimo, delay_maximo))

    # Guardar el dataset completo en Parquet
    df_total.to_parquet(ruta_salida, index=False)

    end_time = time.time()
    horas_transcurridas = (end_time - start_time) / 3600
    
    print(f"\n[!] ¡Extracción de Base de Datos completada!")
    print(f"[!] Total de registros estructurados guardados: {registros_totales_guardados:,}")
    print(f"[!] Días sin reporte en el servidor: {len(dias_fallidos)}")
    print(f"[!] Dataset maestro guardado en: {ruta_salida}")
    print(f"[!] Tiempo total de ejecución: {horas_transcurridas:.2f} horas.")

if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except:
        pass
    extraer_historico_api_json()