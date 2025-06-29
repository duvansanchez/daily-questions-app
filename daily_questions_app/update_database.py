import pyodbc

def update_database():
    """Actualiza la base de datos para agregar campos de tiempo a la tabla response"""
    
    # Configuración de conexión
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=localhost;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        # Verificar si los campos ya existen
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'response' 
            AND COLUMN_NAME IN ('start_time', 'response_time', 'user_id')
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Agregar campo user_id si no existe
        if 'user_id' not in existing_columns:
            print("Agregando campo user_id a la tabla response...")
            cursor.execute("""
                ALTER TABLE response 
                ADD user_id INT NULL
            """)
            print("Campo user_id agregado exitosamente!")
        
        # Agregar campo start_time si no existe
        if 'start_time' not in existing_columns:
            print("Agregando campo start_time a la tabla response...")
            cursor.execute("""
                ALTER TABLE response 
                ADD start_time DATETIME NULL
            """)
            print("Campo start_time agregado exitosamente!")
        
        # Agregar campo response_time si no existe
        if 'response_time' not in existing_columns:
            print("Agregando campo response_time a la tabla response...")
            cursor.execute("""
                ALTER TABLE response 
                ADD response_time INT NULL
            """)
            print("Campo response_time agregado exitosamente!")
        
        # Agregar índice para mejorar el rendimiento
        try:
            cursor.execute("""
                CREATE INDEX IX_response_user_date 
                ON response (user_id, date)
            """)
            print("Índice creado exitosamente!")
        except Exception as e:
            print(f"El índice ya existe o no se pudo crear: {e}")
        
        print("Base de datos actualizada exitosamente!")
        
    except Exception as e:
        print(f"Error actualizando la base de datos: {str(e)}")
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == "__main__":
    update_database()
