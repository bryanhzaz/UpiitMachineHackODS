#Cargamos librerias necesarias
import os
import time
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import MinMaxScaler
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
import warnings

warnings.filterwarnings('ignore')

#Mapeamos los estados de la República Mexicana para normalizar el proceso
MAPEO_ESTADOS_ISO = {
    'AGUASCALIENTES': 'MX-AGU', 'BAJA CALIFORNIA': 'MX-BCN', 'BAJA CALIFORNIA SUR': 'MX-BCS',
    'CAMPECHE': 'MX-CAM', 'CHIAPAS': 'MX-CHP', 'CHIHUAHUA': 'MX-CHH', 'COAHUILA': 'MX-COA',
    'COLIMA': 'MX-COL', 'DISTRITO FEDERAL': 'MX-CMX', 'CIUDAD DE MEXICO': 'MX-CMX', 
    'DURANGO': 'MX-DUR', 'GUANAJUATO': 'MX-GUA', 'GUERRERO': 'MX-GRO', 'HIDALGO': 'MX-HID', 
    'JALISCO': 'MX-JAL', 'MEXICO': 'MX-MEX', 'MICHOACAN': 'MX-MIC', 'MORELOS': 'MX-MOR', 
    'NAYARIT': 'MX-NAY', 'NUEVO LEON': 'MX-NLE', 'OAXACA': 'MX-OAX', 'PUEBLA': 'MX-PUE', 
    'QUERETARO': 'MX-QUE', 'QUINTANA ROO': 'MX-ROO', 'SAN LUIS POTOSI': 'MX-SLP', 
    'SINALOA': 'MX-SIN', 'SONORA': 'MX-SON', 'TABASCO': 'MX-TAB', 'TAMAULIPAS': 'MX-TAM', 
    'TLAXCALA': 'MX-TLA', 'VERACRUZ': 'MX-VER', 'YUCATAN': 'MX-YUC', 'ZACATECAS': 'MX-ZAC'
}

def preprocesar_dataset():
    #Función principal que preprocesa el dataset
    print("Iniciando Preprocesamiento de Machine Learning...")
    start_time = time.time()
    
    ruta_entrada = '../datos/dataset_bruto_total.parquet'
    ruta_salida = '../datos/dataset_limpio_modelo.parquet'
    
    print("Cargando dataset bruto...")
    df = pd.read_parquet(ruta_entrada)
    
    #RENOMBRAMIENTO Y MAPEADO DE COLUMNAS
    print("Mapeando variables a formato final...")
    
    df['fechamonitoreo'] = pd.to_datetime(df['fechamonitoreo'])
    df.rename(columns={'fechamonitoreo': 'fecha'}, inplace=True)
    
    #Creamos un ID numérico para ML, pero conservamos la clavesih original
    df['presa_id'] = pd.factorize(df['clavesih'])[0] + 1
    #Renombramos las columnas para que sean más fáciles de usar
    df.rename(columns={
        'nombreoficial': 'nombre_presa',
        'llenano': 'nivel_hidrico_pct',
        'almacenaactual': 'volumen_hm3'
    }, inplace=True)
    
    #Limpiamos el estado y mapeamos a código MX
    df['estado_limpio'] = df['estado'].astype(str).str.upper().str.replace('Á','A').str.replace('É','E').str.replace('Í','I').str.replace('Ó','O').str.replace('Ú','U').str.strip()
    df['estado_id'] = df['estado_limpio'].map(MAPEO_ESTADOS_ISO).fillna('MX-DESC')
    
    #Seleccionamos las variables de interés (AQUÍ AÑADIMOS clavesih por si es necesario realizar un cruce de datos extra)
    cols_base = ['fecha', 'presa_id', 'clavesih', 'nombre_presa', 'estado_id', 'latitud', 'longitud', 
                 'lluvia_mm', 'evaporacion_mm', 'temp_max_c', 'nivel_hidrico_pct', 'volumen_hm3']
    df = df[cols_base]
    
    #Ordenamos cronológicamente para que la imputación tenga sentido
    df.sort_values(by=['presa_id', 'fecha'], inplace=True)
    
    #IMPUTACIÓN MÚLTIPLE / INTERPOLACIÓN
    print("Aplicando imputación de datos adyacentes para valores nulos...")
    
    cols_a_imputar = ['lluvia_mm', 'evaporacion_mm', 'temp_max_c', 'nivel_hidrico_pct', 'volumen_hm3']
    
    #Usamos .transform() para interpolar los valores nulos 
    df[cols_a_imputar] = df.groupby('presa_id')[cols_a_imputar].transform(lambda x: x.interpolate(method='linear', limit_direction='both'))
    
    #Imputación Múltiple para huecos restantes
    imputer = IterativeImputer(random_state=42, max_iter=10)
    df[cols_a_imputar] = imputer.fit_transform(df[cols_a_imputar])
    
    #ELIMINACIÓN DE ATÍPICOS (Z-SCORE)
    print("Detectando y eliminando valores atípicos (Z-Score > 3)...")
    len_antes = len(df)
    
    cols_zscore = ['nivel_hidrico_pct', 'volumen_hm3']
    
    # Z-scores agrupados por presa
    z_scores = df.groupby('presa_id')[cols_zscore].transform(lambda x: np.abs(stats.zscore(x, nan_policy='omit')))
    
    # Filtro: (Z < 3). Llenamos NaNs en el cálculo z_score con 0 para no perder filas buenas
    filtro_z = (z_scores.fillna(0) < 3).all(axis=1) 
    df = df[filtro_z]
    
    len_despues = len(df)
    print(f"-> Se eliminaron {len_antes - len_despues:,} registros atípicos/anómalos.")

    #NORMALIZACIÓN MIN-MAX (Escalado) esto ayudará a la convergencia del modelo Transformer
    print("Aplicando Normalización Min-Max [0, 1]...")
    
    cols_a_escalar = ['lluvia_mm', 'evaporacion_mm', 'temp_max_c', 'nivel_hidrico_pct', 'volumen_hm3']
    #Escalamos los datos para que estén en un rango de 0 a 1 para que el modelo pueda aprender mejor
    scaler = MinMaxScaler(feature_range=(0, 1))
    cols_escaladas = [f"{col}_escalado" for col in cols_a_escalar]
    
    df[cols_escaladas] = scaler.fit_transform(df[cols_a_escalar])
    
    #Estructura final con clavesih asegurado como llave foránea 
    columnas_finales = [
        'fecha', 'presa_id', 'clavesih', 'nombre_presa', 'estado_id', 'latitud', 'longitud',
        'lluvia_mm', 'evaporacion_mm', 'temp_max_c', 'nivel_hidrico_pct', 'volumen_hm3',
        'lluvia_mm_escalado', 'evaporacion_mm_escalado', 'temp_max_c_escalado', 
        'nivel_hidrico_pct_escalado', 'volumen_hm3_escalado'
    ]
    
    df_final = df[columnas_finales]
    
    os.makedirs('../datos', exist_ok=True)
    df_final.to_parquet(ruta_salida, index=False)
    
    minutos = (time.time() - start_time) / 60
    print("DATASET PREPARADO PARA ENTRENAMIENTO")
    print(f"Registros finales limpios : {len(df_final):,}")
    print(f"Columnas estructuradas    : {len(df_final.columns)} (Clave SIH conservada)")
    print(f"Atípicos eliminados       : {len_antes - len_despues:,}")
    print(f"Archivo listo en          : {ruta_salida}")
    print(f"Tiempo de procesamiento   : {minutos:.2f} minutos")

if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except:
        pass
    preprocesar_dataset()