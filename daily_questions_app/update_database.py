import pyodbc

def update_database():
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-PIDFCJG;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Actualizando la estructura de la tabla response...")
        
        # Modificar la columna response para permitir textos más largos
        cursor.execute('''
            ALTER TABLE response 
            ALTER COLUMN response NVARCHAR(MAX) NOT NULL
        ''')
        
        conn.commit()
        print("Base de datos actualizada exitosamente. La tabla response ahora acepta textos largos.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    print("Actualizando la estructura de la base de datos...")
    update_database()
