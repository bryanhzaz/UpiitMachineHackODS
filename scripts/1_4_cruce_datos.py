#Hacemos la importación de las librerías necesarias
import os
import time
import numpy as np
import pandas as pd
from io import StringIO
from datetime import datetime
from joblib import Parallel, delayed
from tqdm import tqdm
import warnings

# Suprimimos advertencias de pandas sobre tipos de datos para no ensuciar la consola
warnings.filterwarnings('ignore')

# Rutas de los archivos
RUTA_PRESAS = '../datos/historico_presas_conagua_api.parquet'
RUTA_ESTACIONES = '../datos/estaciones_climatologicas.csv'
DIRECTORIO_TXT = '../datos/estaciones_smn_txt/'
RUTA_SALIDA = '../datos/dataset_bruto_total.parquet'

# Rango de fechas para la auditoría de calidad de los datos
FECHA_INICIO_AUDITORIA = pd.to_datetime('1995-01-01')
FECHA_FIN_AUDITORIA = pd.to_datetime('2025-04-23')
CALENDARIO_IDEAL = pd.date_range(start=FECHA_INICIO_AUDITORIA, end=FECHA_FIN_AUDITORIA)

def calcular_distancias(lat_presa, lon_presa, df_estaciones):
    #Calcula la distancia euclideana vectorizada contra todas las estaciones
    #Esto se hace para encontrar las estaciones más cercanas a cada presa y hacer el cruce de datos
    #Se utiliza la fórmula de la distancia euclidiana: sqrt((x2 - x1)^2 + (y2 - y1)^2)
    lats = df_estaciones['latitud'].values
    lons = df_estaciones['longitud'].values
    distancias = np.sqrt((lat_presa - lats)**2 + (lon_presa - lons)**2)
    #Retorna las distancias calculadas
    return distancias

def parsear_txt_clima(id_estacion):
    #Lee y limpia el TXT de una estación específica
    id_pad = str(id_estacion).zfill(5)
    #Se crea la ruta del archivo txt con el id de la estación
    ruta_txt = os.path.join(DIRECTORIO_TXT, f"dia{id_pad}.txt")
    
    if not os.path.exists(ruta_txt):
        # DataFrame vacío si el archivo no existe
        return pd.DataFrame() 
        
    try:
        #Se abre el archivo txt y se lee
        with open(ruta_txt, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
        #Se busca la línea que contiene la cabecera de los datos
        inicio_datos = -1
        for i, linea in enumerate(lineas):
            if 'FECHA' in linea and 'PRECIP' in linea and 'EVAP' in linea:
                inicio_datos = i + 2
                break
        #Si no se encuentra la cabecera, se retorna un DataFrame vacío
        if inicio_datos == -1: return pd.DataFrame()
        #Se une el texto de las líneas para formar el DataFrame
        texto_datos = ''.join(lineas[inicio_datos:])
        
        # Leemos el TXT y se crea el DataFrame
        df = pd.read_csv(StringIO(texto_datos), sep=r'\s+', header=None, 
                         names=['fechamonitoreo', 'lluvia_mm', 'evaporacion_mm', 'temp_max_c', 'temp_min_c'],
                         on_bad_lines='skip')
        
        #Se reemplazan los valores nulos por NaN
        df.replace('NULO', np.nan, inplace=True)
        #Se convierte la columna fechamonitoreo a datetime
        df['fechamonitoreo'] = pd.to_datetime(df['fechamonitoreo'], errors='coerce')
        
        # Se fuerza que las métricas sean números (los Nulos reales se vuelven NaN)
        cols_numericas = ['lluvia_mm', 'evaporacion_mm', 'temp_max_c', 'temp_min_c']
        for col in cols_numericas:
            #Se convierte la columna a numérica
            df[col] = pd.to_numeric(df[col], errors='coerce')
        #Se eliminan las filas con fechas nulas
        return df.dropna(subset=['fechamonitoreo'])
    except:
        return pd.DataFrame()

def auditar_calidad_estacion(df_clima):
    #Cuenta cuántos valores faltan en el periodo 1995 - 2025
    if df_clima.empty:
        return float('inf') 
        
    # Filtramos el clima para el periodo de interés
    df_periodo = df_clima[(df_clima['fechamonitoreo'] >= FECHA_INICIO_AUDITORIA) & 
                          (df_clima['fechamonitoreo'] <= FECHA_FIN_AUDITORIA)]
    
    # Cruzamos con el calendario ideal. Si a la estación le faltan DÍAS completos, 
    # esto los revelará como filas llenas de NaNs.
    df_eval = pd.DataFrame({'fechamonitoreo': CALENDARIO_IDEAL})
    df_eval = pd.merge(df_eval, df_periodo, on='fechamonitoreo', how='left')
    
    # Contamos la cantidad total de NaNs en las 3 variables clave
    # Le damos más peso a que existan lluvia, evaporación y temp_max.
    total_nulos = df_eval[['lluvia_mm', 'evaporacion_mm', 'temp_max_c']].isna().sum().sum()
    return total_nulos

def procesar_una_presa(df_presa, df_estaciones):
    #Función Worker (Ejecutada en paralelo):
    #Recibe los datos históricos de una presa, busca sus 5 vecinas, elige la mejor y hace el join.
    #Sacar lat y lon de esta presa (tomamos la de la primera fila)
    lat_presa = df_presa['latitud'].iloc[0]
    lon_presa = df_presa['longitud'].iloc[0]
    clavesih = df_presa['clavesih'].iloc[0]
    
    #Calcular distancias contra todas las estaciones del catálogo
    distancias = calcular_distancias(lat_presa, lon_presa, df_estaciones)
    
    #Obtener los índices de las 5 estaciones más cercanas
    idx_top5 = np.argsort(distancias)[:5]
    estaciones_top5 = df_estaciones.iloc[idx_top5]
    
    mejor_estacion_id = None
    min_nulos = float('inf')
    mejor_df_clima = pd.DataFrame()
    
    #Auditar a las 5 candidatas
    for _, estacion in estaciones_top5.iterrows():
        id_estacion = estacion['numero']
        df_clima_candidato = parsear_txt_clima(id_estacion)
        
        nulos_candidato = auditar_calidad_estacion(df_clima_candidato)
        
        if nulos_candidato < min_nulos:
            min_nulos = nulos_candidato
            mejor_estacion_id = id_estacion
            mejor_df_clima = df_clima_candidato
            
    #Hacer el Join final para esta presa con el ganador
    df_presa_procesada = df_presa.copy()
    df_presa_procesada['estacion_clima_id'] = mejor_estacion_id
    
    if not mejor_df_clima.empty:
        #Hacemos el cruce (Left Join) respetando el histórico de la presa
        df_presa_procesada = pd.merge(df_presa_procesada, mejor_df_clima, 
                                      on='fechamonitoreo', how='left')
    else:
        # Si las 5 estaciones fallaron (solo si fueron mal descargados los datos), creamos las columnas vacías
        for col in ['lluvia_mm', 'evaporacion_mm', 'temp_max_c', 'temp_min_c']:
            df_presa_procesada[col] = np.nan
            
    return df_presa_procesada

def orquestador_cruce_masivo():
    #Función principal que orquesta el cruce de datos
    print("Iniciando Fase 4: Cruce Espacial y Auditoría de Calidad con Multiprocessing...")
    start_time = time.time()
    
    #Carga de datos a la RAM
    print("Cargando CSV masivo de presas y catálogo de estaciones...")
    df_presas_master = pd.read_parquet(RUTA_PRESAS)
    df_presas_master['fechamonitoreo'] = pd.to_datetime(df_presas_master['fechamonitoreo'])
    
    df_estaciones = pd.read_csv(RUTA_ESTACIONES)
    
    #Validar que los TXT existen
    if not os.path.exists(DIRECTORIO_TXT) or len(os.listdir(DIRECTORIO_TXT)) == 0:
        print(f"No se encontraron los archivos TXT en {DIRECTORIO_TXT}")
        return

    #Dividir el trabajo (Un grupo por cada presa única)
    print(f"Agrupando registros por 'clavesih' para paralelizar...")
    # Agrupamos y convertimos a una lista de DataFrames (cada uno es una presa)
    grupos_presas = [grupo for _, grupo in df_presas_master.groupby('clavesih')]
    num_presas = len(grupos_presas)
    
    print(f"Se detectaron {num_presas} presas únicas.")
    print(f"Lanzando workers en paralelo")
    
    #EJECUCIÓN PARALELA CON JOBLIB
    # n_jobs=-1 usa el 100% de los núcleos
    resultados_procesados = Parallel(n_jobs=-1)(
        delayed(procesar_una_presa)(df_grupo, df_estaciones) 
        for df_grupo in tqdm(grupos_presas, desc="Procesando Presas", unit="presa")
    )
    
    #Consolidación del Dataset Final
    print("\nUnificando los resultados en el dataset bruto total...")
    df_bruto_total = pd.concat(resultados_procesados, ignore_index=True)
    
    #Ordenar cronológicamente y por presa para que quede presentable
    df_bruto_total.sort_values(by=['fechamonitoreo', 'clavesih'], inplace=True)
    
    #Guardar a disco
    os.makedirs('../datos', exist_ok=True)
    df_bruto_total.to_parquet(RUTA_SALIDA, index=False)
    
    #Métricas y Tiempo
    end_time = time.time()
    minutos = (end_time - start_time) / 60
    
    print("REPORTE DE INGENIERÍA DE DATOS (FASE 4)")
    print(f"Total de presas procesadas     : {num_presas}")
    print(f"Total de registros en CSV      : {len(df_bruto_total):,}")
    print(f"Columnas nuevas integradas     : lluvia_mm, evaporacion_mm, temp_max_c, temp_min_c")
    print(f"Archivo BRUTO listo en         : {RUTA_SALIDA}")
    print(f"Tiempo total de ejecución      : {minutos:.2f} minutos.")

if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except:
        pass
    orquestador_cruce_masivo()