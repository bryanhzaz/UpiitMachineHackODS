import os
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings

warnings.filterwarnings('ignore')

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class TransformerRegressor(nn.Module):
    def __init__(self, input_dim, d_model, nhead, num_layers, dropout=0.1):
        super(TransformerRegressor, self).__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        self.pos_encoder = nn.Parameter(torch.zeros(1, 500, d_model)) 
        encoder_layers = nn.TransformerEncoderLayer(d_model, nhead, d_model*2, dropout, batch_first=True)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
        self.decoder = nn.Linear(d_model, 1)

    def forward(self, x):
        x = self.embedding(x)
        x = x + self.pos_encoder[:, :x.size(1), :]
        x = self.transformer_encoder(x)
        x = self.decoder(x[:, -1, :])
        return x

def ejecutar_pipeline_transformer():
    print("Iniciando Fase 6 (VERSION MEJORADA): Entrenamiento y Prediccion Real...")
    ruta_input = '/content/drive/MyDrive/datosHackods/dataset_limpio_modelo.csv'
    if not os.path.exists(ruta_input):
        print(f"Error: No se encontró el dataset en {ruta_input}")
        return
        
    df = pd.read_csv(ruta_input, low_memory=False)
    
    features = [
        'latitud', 'longitud', 'lluvia_mm_escalado', 'evaporacion_mm_escalado', 
        'temp_max_c_escalado', 'nivel_hidrico_pct_escalado', 'volumen_hm3_escalado'
    ]
    target = 'nivel_hidrico_pct_escalado'

    print("Creando ventanas temporales para el modelo...")
    def create_sequences(data, seq_length):
        xs, ys = [], []
        for i in range(len(data) - seq_length):
            x = data[i:(i + seq_length), :]
            y = data[i + seq_length, -1] 
            xs.append(x)
            ys.append(y)
        return np.array(xs), np.array(ys)
        
    data_matrix = df[features + [target]].values
    X, y = create_sequences(data_matrix, seq_length=10)
    
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
    train_data = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
    val_data = TensorDataset(torch.FloatTensor(X_val), torch.FloatTensor(y_val))
    train_loader = DataLoader(train_data, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_data, batch_size=64)

    model = TransformerRegressor(input_dim=len(features)+1, d_model=64, nhead=4, num_layers=2).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    print("Arquitectura del transformer")
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total de parámetros      : {total_params:,}")
    print(f"Parámetros entrenables   : {trainable_params:,}")
    
    epocas = 5 
    print(f"Iniciando entrenamiento en {device.type.upper()} por {epocas} épocas...")
    start_train_time = time.time()
    
    for epoch in range(epocas):
        model.train() 
        epoch_train_loss = 0.0
        train_batches = 0
        
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            output = model(batch_x)
            loss = criterion(output.squeeze(), batch_y) 
            loss.backward()
            optimizer.step()
            epoch_train_loss += loss.item()
            train_batches += 1
            
        avg_train_loss = epoch_train_loss / train_batches
        
        model.eval()
        epoch_val_loss = 0.0
        val_batches = 0
        
        with torch.no_grad(): 
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                output = model(batch_x)
                loss = criterion(output.squeeze(), batch_y)
                epoch_val_loss += loss.item()
                val_batches += 1
                
        avg_val_loss = epoch_val_loss / val_batches
        print(f" -> Época [{epoch+1:02d}/{epocas}] | Train Loss: {avg_train_loss:.5f} | Val Loss: {avg_val_loss:.5f}")
        
    train_duration_sec = time.time() - start_train_time
    print(f"Entrenamiento finalizado en {train_duration_sec / 60:.2f} minutos.")

    print("\nEvaluando el modelo con datos de validación...")
    model.eval()
    preds_val = []
    with torch.no_grad():
        for batch_x, _ in val_loader:
            batch_x = batch_x.to(device)
            preds_val.extend(model(batch_x).cpu().numpy())
    
    mae = mean_absolute_error(y_val, preds_val)
    mse = mean_squared_error(y_val, preds_val)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_val, preds_val)
    
    print(f"MAE  (Error Absoluto Medio) : {mae:.4f}")
    print(f"MSE  (Error Cuadrático M.)  : {mse:.4f}")
    print(f"RMSE (Raíz del MSE)         : {rmse:.4f}")
    print(f"R^2  (Coef. Determinación)  : {r2:.4f}")


    print("\nGenerando escenarios de predicción reales con redes neuronales (+1°C, +2°C, +3°C)...")
    
    # Valores de desescalado (Inversa de MinMaxScaler basado en el dataset general)
    min_pct = df['nivel_hidrico_pct'].min()
    max_pct = df['nivel_hidrico_pct'].max()
    min_temp = df['temp_max_c'].min()
    max_temp = df['temp_max_c'].max()
    
    def unscale_pct(val_escalado):
        return val_escalado * (max_pct - min_pct) + min_pct

    scenarios_df_list = []
    seq_length = 10
    columnas_entrada = features + [target]
    temp_idx = columnas_entrada.index('temp_max_c_escalado')
    
    with torch.no_grad():
        presas = df['clavesih'].unique()
        for presa in presas:
            # Tomamos el historial de la presa ordenado
            df_presa = df[df['clavesih'] == presa]
            if len(df_presa) < seq_length:
                continue
                
            last_records = df_presa.tail(seq_length).copy()
            ultimo_reg = last_records.iloc[-1]
            
            pct_actual = ultimo_reg['nivel_hidrico_pct']
            vol_actual = ultimo_reg['volumen_hm3']
            # Factor de proporción entre nivel en % y volumen hm3 de la presa para inferencia final
            vol_factor = vol_actual / pct_actual if pct_actual > 0 else 0
            
            row_dict = {
                'presa_id': ultimo_reg['presa_id'],
                'clavesih': presa,
                'nombre_presa': ultimo_reg['nombre_presa'],
                'estado_id': ultimo_reg['estado_id'],
                'latitud': ultimo_reg['latitud'],
                'longitud': ultimo_reg['longitud'],
                'pred_vol_Base': vol_actual,
                'pred_pct_Base': pct_actual,
                'pred_pct_base_baja': pct_actual * 0.95,
                'pred_pct_base_alta': pct_actual * 1.05
            }
            
            # Matriz de los últimos seq_length días
            base_matrix = last_records[columnas_entrada].values
            temps_originales_unscaled = last_records['temp_max_c'].values
            
            # Iterar escenarios de clima
            for incremento in [1, 2, 3]:
                matriz_escenario = base_matrix.copy()
                
                # Modificamos temperatura real (en unscaled) con el incremento 
                # y re-escalamos según el MinMaxScaler original
                new_temps_real = temps_originales_unscaled + incremento
                new_temps_scaled = [(t - min_temp) / (max_temp - min_temp) for t in new_temps_real]
                matriz_escenario[:, temp_idx] = new_temps_scaled
                
                # Transformamos la secuencia e inferimos (añadiendo el batch temporal (1, seq, var))
                tensor_input = torch.FloatTensor(matriz_escenario).unsqueeze(0).to(device)
                pred_pct_escalado = model(tensor_input).cpu().numpy()[0][0]
                
                # Desescalamos el resultado porcentual y limitamos lógicamente (0 - 100%)
                pred_pct_real = unscale_pct(pred_pct_escalado)
                if pred_pct_real > 100.0: pred_pct_real = 100.0
                if pred_pct_real < 0.0: pred_pct_real = 0.0
                
                # Extrapolamos volumen según factor de nivel
                pred_vol_real = pred_pct_real * vol_factor
                
                # Guardamos resultado
                row_dict[f'pred_vol_Temp_+{incremento}C'] = pred_vol_real
                row_dict[f'pred_pct_Temp_+{incremento}C'] = pred_pct_real
                
            scenarios_df_list.append(row_dict)

    output_df = pd.DataFrame(scenarios_df_list)
    
    # Guardar resultados
    ruta_final = '/content/drive/MyDrive/datosHackods/predicciones_finales_smn.csv'
    os.makedirs(os.path.dirname(ruta_final), exist_ok=True)
    output_df.to_csv(ruta_final, index=False)
    
    print(f"\nArchivo final de inferencia de red neuronal generado en: {ruta_final}")

if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except:
        pass
    ejecutar_pipeline_transformer()
