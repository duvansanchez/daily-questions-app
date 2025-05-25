import pyodbc

conn_str = (
    "DRIVER={SQL Server};"
    "SERVER=DESKTOP-32COF63;"
    "DATABASE=DailyQuestions;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Verificar si la columna existe
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.columns 
            WHERE object_id = OBJECT_ID('question') 
            AND name = 'categoria'
        )
        BEGIN
            ALTER TABLE question ADD categoria NVARCHAR(100)
        END
    """)
    
    conn.commit()
    print("Columna 'categoria' añadida exitosamente o ya existía")
    
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    try:
        conn.close()
    except:
        pass 