import mysql.connector

def insertar_datos_rrss(fecha, alcance, clics):
    config = {
        "host": "217.160.158.217",
        "database": "MEDIOS_DIGITALES",
        "user": "user_md_new",
        "password": "md_secuo_c13.$2025"
    }
    
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        query = """
            INSERT INTO RRSS_diarias (fecha, alcance_face, clics_face)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            alcance_face = VALUES(alcance_face),
            clics_face = VALUES(clics_face)
        """
        
        cursor.execute(query, (fecha, alcance, clics))
        conn.commit()
        print(f"✅ Datos de RRSS insertados/actualizados para la fecha {fecha}")
        
    except mysql.connector.Error as e:
        print(f"❌ Error: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Ejemplo de uso:
# insertar_datos_rrss('2025-12-22', 125000, 3800)