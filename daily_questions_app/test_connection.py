import pyodbc

conn_str = (
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-32COF63;"
    "DATABASE=DailyQuestions;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    print("Conexión exitosa!")
    
    # Intentar crear una tabla de prueba
    cursor = conn.cursor()
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'test_table')
        CREATE TABLE test_table (
            id INT PRIMARY KEY,
            name NVARCHAR(50)
        )
    """)
    conn.commit()
    print("Tabla de prueba creada exitosamente!")
    
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    try:
        conn.close()
    except:
        pass
