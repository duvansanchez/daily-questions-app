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
        
        # --- INICIO: Migración tabla objetivos ---
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'objetivos' 
            AND COLUMN_NAME IN (
                'estado', 'fecha_inicio', 'fecha_fin', 'horas_estimadas', 'dificultad', 'etiquetas', 'recompensa', 'notas_adicionales', 'recurrente', 'frecuencia'
            )
        """)
        existing_objetivos_columns = [row[0] for row in cursor.fetchall()]

        if 'estado' not in existing_objetivos_columns:
            print("Agregando campo estado a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD estado NVARCHAR(50) NULL
            """)
            print("Campo estado agregado exitosamente!")
        if 'fecha_inicio' not in existing_objetivos_columns:
            print("Agregando campo fecha_inicio a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD fecha_inicio DATETIME NULL
            """)
            print("Campo fecha_inicio agregado exitosamente!")
        if 'fecha_fin' not in existing_objetivos_columns:
            print("Agregando campo fecha_fin a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD fecha_fin DATETIME NULL
            """)
            print("Campo fecha_fin agregado exitosamente!")
        if 'horas_estimadas' not in existing_objetivos_columns:
            print("Agregando campo horas_estimadas a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD horas_estimadas FLOAT NULL
            """)
            print("Campo horas_estimadas agregado exitosamente!")
        if 'dificultad' not in existing_objetivos_columns:
            print("Agregando campo dificultad a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD dificultad INT NULL
            """)
            print("Campo dificultad agregado exitosamente!")
        if 'etiquetas' not in existing_objetivos_columns:
            print("Agregando campo etiquetas a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD etiquetas NVARCHAR(255) NULL
            """)
            print("Campo etiquetas agregado exitosamente!")
        if 'recompensa' not in existing_objetivos_columns:
            print("Agregando campo recompensa a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD recompensa NVARCHAR(255) NULL
            """)
            print("Campo recompensa agregado exitosamente!")
        if 'notas_adicionales' not in existing_objetivos_columns:
            print("Agregando campo notas_adicionales a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD notas_adicionales NVARCHAR(MAX) NULL
            """)
            print("Campo notas_adicionales agregado exitosamente!")
        if 'recurrente' not in existing_objetivos_columns:
            print("Agregando campo recurrente a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD recurrente BIT DEFAULT 0
            """)
            print("Campo recurrente agregado exitosamente!")
        if 'frecuencia' not in existing_objetivos_columns:
            print("Agregando campo frecuencia a la tabla objetivos...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD frecuencia NVARCHAR(20) NULL
            """)
            print("Campo frecuencia agregado exitosamente!")
        # --- FIN: Migración tabla objetivos ---
        
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
