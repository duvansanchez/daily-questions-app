import pyodbc

# Configuración de conexión actualizada
drivers = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server", 
    "SQL Server"
]

def get_connection():
    for driver in drivers:
        try:
            conn_str = (
                f"DRIVER={{{driver}}};"
                "SERVER=DESKTOP-2MR0PJ6;"
                "DATABASE=DailyQuestions;"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
                "Connection Timeout=30;"
            )
            return pyodbc.connect(conn_str)
        except Exception as e:
            print(f"No se pudo conectar con {driver}: {str(e)}")
    raise Exception("No se pudo establecer conexión con ningún controlador ODBC")

try:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verificar si la columna frecuencia existe
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.columns 
            WHERE object_id = OBJECT_ID('question') 
            AND name = 'frecuencia'
        )
        BEGIN
            ALTER TABLE question ADD frecuencia NVARCHAR(20) DEFAULT 'diaria'
        END
    """)
    
    conn.commit()
    print("✓ Columna 'frecuencia' añadida exitosamente o ya existía")
    
    # Verificar la estructura actual de la tabla
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'question'
        ORDER BY ORDINAL_POSITION
    """)
    
    print("\n=== Estructura actual de la tabla question ===")
    for row in cursor.fetchall():
        nullable = "NULL" if row[2] == "YES" else "NOT NULL"
        default = f" DEFAULT {row[3]}" if row[3] else ""
        print(f"  {row[0]} {row[1]} {nullable}{default}")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
finally:
    try:
        conn.close()
    except:
        pass