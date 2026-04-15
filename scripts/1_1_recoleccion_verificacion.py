#Hacemos la importación de las librerías necesarias
import os
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
import urllib3
from tqdm import tqdm

# Desactivamos advertencias de certificados SSL del gobierno
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#El siguiente script permite continuar la descarga de datos en caso de que se haya interrumpido
#Definimos la función para continuar la descarga de datos
def continuar_descarga_historica():
    print("Iniciando continuación de la extracción vía API...")
    start_time = time.time()
    
    # Ajustamos ruta relativa para poder verificar hasta donde están los archivos
    ruta_maestra = '../datos/historico_presas_conagua_api.parquet' 
    URL_BASE = "https://sinav30.conagua.gob.mx:8080/PresasPG/presas/reporte/"
    
    # Verificación del último día existente capturado
    if not os.path.exists(ruta_maestra):
        print(f"No se encontró el archivo maestro en {ruta_maestra}.")
        return

    print(" Leyendo el archivo CSV existente para ubicar el último registro...")
    df_actual = pd.read_parquet(ruta_maestra)
    df_actual['fechamonitoreo'] = pd.to_datetime(df_actual['fechamonitoreo'])
    
    # Encontramos la última fecha y le sumamos 1 día para empezar exactamente desde donde se quedó
    ultima_fecha_csv = df_actual['fechamonitoreo'].max()
    fecha_inicio = ultima_fecha_csv + timedelta(days=1)
    
    # La fecha límite, desde aquí en adelante no hay datos en el servidor
    fecha_limite = datetime(2025, 4, 1)
    
    print(f"\n Último día registrado en el CSV: {ultima_fecha_csv.strftime('%Y-%m-%d')}")
    print(f" Retomando consultas a partir de: {fecha_inicio.strftime('%Y-%m-%d')}")
    print(f" Fecha de paro (Límite): {fecha_limite.strftime('%Y-%m-%d')}")
    
    if fecha_inicio > fecha_limite:
        print("\n La base de datos ya está completa hasta el 1 de abril de 2025. Proceso finalizado.")
        return

    dias_a_descargar = pd.date_range(start=fecha_inicio, end=fecha_limite)
    print(f"\n Total de días por procesar en esta sesión: {len(dias_a_descargar):,}")
    
    # Configuración de la extracción
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    })
    
    # Las columnas exactas que necesitamos para el análisis
    columnas_requeridas = [
        'idmonitoreodiario', 'fechamonitoreo', 'clavesih', 'nombreoficial', 
        'nombrecomun', 'estado', 'nommunicipio', 'regioncna', 'latitud', 
        'longitud', 'uso', 'corriente', 'tipovertedor', 'inicioop', 
        'elevcorona', 'bordolibre', 'nameelev', 'namealmac', 'namoelev', 
        'namoalmac', 'alturacortina', 'elevacionactual', 'almacenaactual', 'llenano'
    ]
    #Definimos estructura de datos para el guardado 
    lote_actual = []
    # Cada 50 días inyecta directo al CSV
    tamano_lote = 50 
    registros_agregados = 0

    # Ciclo de descarga hacia adelante
    for i, fecha in enumerate(tqdm(dias_a_descargar, desc="Descargando registros", unit="día")):
        fecha_str = fecha.strftime('%Y-%m-%d')
        url_api = URL_BASE + fecha_str
        
        try:
            response = session.get(url_api, timeout=15, verify=False)
            
            if response.status_code == 200:
                datos_json = response.json()
                # Si el día tiene registros
                if datos_json: 
                    df_dia = pd.DataFrame(datos_json)
                    
                    # Filtramos y ordenamos para que coincida exactamente con el formato
                    # Si por alguna razón no hubo captura de datos en un día, se rellena con nulos
                    for col in columnas_requeridas:
                        if col not in df_dia.columns:
                            df_dia[col] = None
                    
                    df_dia = df_dia[columnas_requeridas]
                    lote_actual.append(df_dia)
                    
        except Exception as e:
            pass 
            
        # Guardado en tiempo real 
        if len(lote_actual) >= tamano_lote or i == (len(dias_a_descargar) - 1):
            if lote_actual:
                df_lote = pd.concat(lote_actual, ignore_index=True)
                
                
                df_lote.to_csv(ruta_maestra, mode='a', index=False, header=False)
                
                registros_agregados += len(df_lote)
                # Limpiar memoria RAM
                lote_actual = [] 
                
        # Delay aleatorio para evitar bloqueos y acelerar el proceso
        time.sleep(random.uniform(0.5, 1.2))

    end_time = time.time()
    minutos = (end_time - start_time) / 60
    
    print(f"Total de registros nuevos añadidos al CSV: {registros_agregados:,}")
    print(f"Tiempo de ejecución: {minutos:.2f} minutos.")

if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except:
        pass
    continuar_descarga_historica()