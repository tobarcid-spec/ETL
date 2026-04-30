import pandas as pd
import os

# Crear datos de ejemplo
datos_ejemplo = {
    'titulo': ['Programa 1', 'Programa 2', 'Programa 3'],
    'plays': [100, 200, 150]
}

df_ejemplo = pd.DataFrame(datos_ejemplo)
output_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'programacion', '2025-09-04_programacion.xlsx')
df_ejemplo.to_excel(output_file, index=False)
print(f"Archivo de ejemplo creado: {output_file}")