#Hacemos la importación de las librerías necesarias
import os
import time
import requests
import pandas as pd
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#Códigos INEGI mapeados a las carpetas del servidor SMN
MAPEO_ESTADOS = {
    '01': 'ags', '02': 'bc', '03': 'bcs', '04': 'camp', '05': 'coah',
    '06': 'col', '07': 'chis', '08': 'chih', '09': 'df', '10': 'dgo',
    '11': 'gto', '12': 'gro', '13': 'hgo', '14': 'jal', '15': 'mex',
    '16': 'mich', '17': 'mor', '18': 'nay', '19': 'nl', '20': 'oax',
    '21': 'pue', '22': 'qro', '23': 'qroo', '24': 'slp', '25': 'sin',
    '26': 'son', '27': 'tab', '28': 'tamps', '29': 'tlax', '30': 'ver',
    '31': 'yuc', '32': 'zac'
}
#Directorio donde se guardarán los archivos txt
DIRECTORIO_TXT = '../datos/estaciones_smn_txt/'
#Función para extraer los metadatos de los archivos txt
def extraer_metadatos_txt(texto_archivo, id_estacion):
    #Lee el texto crudo y extrae las coordenadas y el nombre de la estación
    metadatos = {'numero': id_estacion, 'nombre': '', 'estado': '', 'latitud': None, 'longitud': None}
    
    lineas = texto_archivo.split('\n')
    #Buscamos solo en la cabecera
    for linea in lineas[:20]: 
        if 'NOMBRE' in linea:
            metadatos['nombre'] = linea.split(':')[1].strip()
        elif 'ESTADO' in linea:
            metadatos['estado'] = linea.split(':')[1].strip()
        elif 'LATITUD' in linea:
            try:
                # Extrae el número quitando el símbolo ° para evitar problemas de lectura
                metadatos['latitud'] = float(linea.split(':')[1].replace('°', '').strip())
            except: pass
        elif 'LONGITUD' in linea:
            try:
                metadatos['longitud'] = float(linea.split(':')[1].replace('°', '').strip())
            except: pass
            
    return metadatos

def intentar_descargar(estado_codigo, carpeta_estado, num_estacion):
    #Función que prueba si una estación existe, la descarga y extrae sus datos
    #Formateamos el número (ej. estado 08, estacion 350 -> 08350)
    num_pad = str(num_estacion).zfill(3)
    id_estacion = f"{estado_codigo}{num_pad}"
    #URL de cualquier estación 
    url = f"https://smn.conagua.gob.mx/tools/RESOURCES/Normales_Climatologicas/Diarios/{carpeta_estado}/dia{id_estacion}.txt"
    ruta_guardado = os.path.join(DIRECTORIO_TXT, f"dia{id_estacion}.txt")
    
    #Manejo de reconexión y sesión limpia por hilo
    try:
        res = requests.get(url, verify=False, timeout=5)
        
        # Si el servidor dice OK y el texto tiene la cabecera válida
        if res.status_code == 200 and "COMISIÓN NACIONAL DEL AGUA" in res.text:
            # 1. Guardar en disco formación de un pequeño Data Lake
            with open(ruta_guardado, 'w', encoding='utf-8') as f:
                f.write(res.text)
                
            # 2. Extraer catálogo en vivo
            metadatos = extraer_metadatos_txt(res.text, id_estacion)
            
            # Solo devolvemos éxito si realmente pudimos leer las coordenadas
            if metadatos['latitud'] is not None and metadatos['longitud'] is not None:
                return (True, metadatos)
                
        return (False, None)
    except:
        return (False, None)

def escaneo_total_pais():
    print("Iniciando Fase 3.1: Escaneo Nacional a Ciega y Construcción de Catálogo...")
    start_time = time.time()
    
    os.makedirs(DIRECTORIO_TXT, exist_ok=True)
    
    # Generamos la lista de las 32,000 combinaciones posibles dado el número de estados y el número de estaciones por estado
    combinaciones = []
    for cod_estado, carpeta in MAPEO_ESTADOS.items():
        for i in range(1000): # Del 000 al 999
            combinaciones.append((cod_estado, carpeta, i))
            
    print(f"Generadas {len(combinaciones):,} URLs posibles para validar.")
    print("Lanzando 30 hilos paralelo.")

    catalogo_creado = []
    exitos = 0
    
    # Hacemos uso de cómputo de alto rendimiento para descargar los datos
    # Multi-threading para probar miles de URLs por minuto
    with ThreadPoolExecutor(max_workers=30) as executor:
        # Enviar todas las tareas al executor
        futuros = [executor.submit(intentar_descargar, c[0], c[1], c[2]) for c in combinaciones]
        
        # Procesar los resultados a medida que van llegando
        for futuro in tqdm(as_completed(futuros), total=len(futuros), desc="Escaneando el país"):
            existe, datos_estacion = futuro.result()
            if existe:
                catalogo_creado.append(datos_estacion)
                exitos += 1

    # Guardar el catálogo generado
    if catalogo_creado:
        df_catalogo = pd.DataFrame(catalogo_creado)
        ruta_catalogo = '../datos/estaciones_climatologicas.csv'
        df_catalogo.to_csv(ruta_catalogo, index=False)
        print(f"\nCatálogo creado exitosamente en {ruta_catalogo}")
    else:
        print("\nError crítico: La red bloqueó las peticiones o no se encontraron estaciones.")

    minutos = (time.time() - start_time) / 60
    print("REPORTE DE EXTRACCIÓN METEOROLÓGICA")
    print(f"Estaciones válidas descargadas : {exitos:,}")
    print(f"URLs vacías (404) ignoradas    : {len(combinaciones) - exitos:,}")
    print(f"Tiempo total de escaneo        : {minutos:.2f} minutos.")
#Se ejecuta la función
if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except:
        pass
    escaneo_total_pais()