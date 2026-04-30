import os
import pandas as pd
from datetime import datetime
import glob

# Definir la carpeta donde están los archivos Excel
carpeta = os.path.join(os.path.dirname(__file__), '..', 'data', 'programacion')

# Lista de archivos Excel en la carpeta
archivos_excel = glob.glob(os.path.join(carpeta, '*.xlsx'))

# Lista para almacenar los datos procesados
datos_procesados = []

# Procesar cada archivo
for archivo in archivos_excel:
    # Extraer la fecha del nombre del archivo (asumiendo formato YYYY-MM-DD_programacion.xlsx)
    nombre_base = os.path.basename(archivo)
    fecha_str = nombre_base.split('_')[0]  # e.g., '2025-09-04'
    
    # Convertir a datetime
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
    
    # Obtener el día de la semana (0=lunes, 6=domingo)
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dia_semana = dias_semana[fecha.weekday()]
    
    # Leer el Excel
    try:
        df = pd.read_excel(archivo)
        
        # Asumir que el Excel tiene columnas 'Título' (programa) y 'Plays'
        # Si no, ajustar según sea necesario
        if 'Título' in df.columns and 'Plays' in df.columns:
            for _, row in df.iterrows():
                titulo = row['Título']
                plays = row['Plays']
                # Filtrar filas en blanco, None, o que contengan "total" (case insensitive)
                if pd.isna(titulo) or str(titulo).strip() == '' or 'total' in str(titulo).lower():
                    continue
                # También filtrar si plays es NaN
                if pd.isna(plays):
                    continue
                datos_procesados.append({
                    'titulo': titulo,
                    'plays': plays,
                    'dia_semana': dia_semana,
                    'fecha': fecha_str
                })
        else:
            print(f"Advertencia: El archivo {archivo} no tiene las columnas esperadas 'titulo' y 'plays'. Columnas encontradas: {list(df.columns)}")
    
    except Exception as e:
        print(f"Error al procesar {archivo}: {e}")

# Crear DataFrame con todos los datos
if datos_procesados:
    df_final = pd.DataFrame(datos_procesados)
    
    # Guardar en Excel
    output_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'reporte_programacion.xlsx')
    df_final.to_excel(output_file, index=False)
    print(f"Excel generado exitosamente: {output_file}")
    print(f"Total de registros procesados: {len(df_final)}")
else:
    print("No se encontraron datos para procesar.")