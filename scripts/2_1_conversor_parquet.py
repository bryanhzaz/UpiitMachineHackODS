import pandas as pd
import os

# Lista de archivos CSV a convertir
files_to_convert = [
    'datos/historico_presas_conagua_api.csv',
    'datos/dataset_bruto_total.csv',
    'datos/dataset_limpio_modelo.csv'
]

for csv_file in files_to_convert:
    if os.path.exists(csv_file):
        print(f"Convirtiendo {csv_file} a Parquet...")
        df = pd.read_csv(csv_file, low_memory=False)
        parquet_file = csv_file.replace('.csv', '.parquet')
        df.to_parquet(parquet_file, index=False)
        print(f"Convertido: {parquet_file}")
    else:
        print(f"Archivo no encontrado: {csv_file}")

print("Conversión completada.")