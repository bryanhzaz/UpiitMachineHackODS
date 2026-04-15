#Hacemos la importación de las librerías necesarias
import os
import pandas as pd
from datetime import datetime

#Definimos la función para analizar la integridad del conjunto de datos
def analizar_integridad_temporal():
    print("Iniciando escaneo de integridad temporal del dataset...")
    
    ruta_maestra = '../datos/historico_presas_conagua_api.parquet'
    
    if not os.path.exists(ruta_maestra):
        print(f" Error: No se encontró el archivo en {ruta_maestra}")
        return

    print("[*] Cargando las fechas del archivo maestro (esto tomará unos segundos)...")
    
    # Solo leemos la columna de fechas para no saturar la memoria RAM
    df = pd.read_parquet(ruta_maestra, columns=['fechamonitoreo'])
    
    # Convertimos a formato fecha real de Pandas
    df['fechamonitoreo'] = pd.to_datetime(df['fechamonitoreo'], errors='coerce')
    
    # Eliminamos cualquier valor nulo que pudiera existir por errores de guardado
    df = df.dropna(subset=['fechamonitoreo'])
    
    # Obtenemos los días únicos que realmente existen en tu base de datos
    dias_existentes = pd.to_datetime(df['fechamonitoreo'].dt.date.unique())
    
    if len(dias_existentes) == 0:
        print("El archivo está vacío o no tiene fechas válidas.")
        return

    fecha_minima = dias_existentes.min()
    fecha_maxima = dias_existentes.max()
    
    # Construimos el calendario ideal: todos los días que deberían existir
    calendario_ideal = pd.date_range(start=fecha_minima, end=fecha_maxima)
    
    # Calculamos los huecos (días que están en el calendario ideal pero no en el CSV)
    huecos = calendario_ideal.difference(dias_existentes)
    
    print("Reporte de forma de datos")
    print(f" Primer día registrado : {fecha_minima.strftime('%Y-%m-%d')}")
    print(f" Último día registrado : {fecha_maxima.strftime('%Y-%m-%d')}")
    print(f" Días totales esperados : {len(calendario_ideal):,}")
    print(f" Días reales en el CSV  : {len(dias_existentes):,}")
    print(f" Días FALTANTES (Huecos): {len(huecos):,}")
    
    if len(huecos) > 0:
        # Guardamos la lista de huecos en un txt para que los tengas a la mano
        ruta_reporte = '../datos/reporte_dias_faltantes.txt'
        with open(ruta_reporte, 'w') as f:
            f.write(f"Reporte de dias faltantes entre {fecha_minima.strftime('%Y-%m-%d')} y {fecha_maxima.strftime('%Y-%m-%d')}\n")
            f.write("="*60 + "\n")
            for h in huecos:
                f.write(f"{h.strftime('%Y-%m-%d')}\n")
                
        print(f"\n Se encontró que faltan {len(huecos)} días en tu base de datos.")
        print(f" Se ha generado un archivo de texto con la lista exacta de los días faltantes en:")
        print(f"  -> {ruta_reporte}")
        
        # Mostramos una probadita en consola
        print("\nEjemplo de algunos días faltantes:")
        for h in huecos[:10]: # Solo muestra los primeros 10
            print(f" - {h.strftime('%Y-%m-%d')}")
        if len(huecos) > 10:
            print(" revisar el archivo .txt para ver la lista completa")
    else:
        print("\n No hay ni un solo hueco")

if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except:
        pass
    analizar_integridad_temporal()