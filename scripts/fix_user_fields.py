import pyodbc

def fix_user_fields():
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-PIDFCJG;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Actualizando tamaños de campos en la tabla user...")
        
        # Aumentar el tamaño del campo username
        cursor.execute('''
            ALTER TABLE [user] 
            ALTER COLUMN username NVARCHAR(100) NOT NULL
        ''')
        
        # Aumentar el tamaño del campo password para los hashes
        cursor.execute('''
            ALTER TABLE [user] 
            ALTER COLUMN password NVARCHAR(255) NOT NULL
        ''')
        
        conn.commit()
        print("Campos de la tabla user actualizados exitosamente!")
        print("- username: NVARCHAR(100)")
        print("- password: NVARCHAR(255)")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    print("Corrigiendo tamaños de campos en la tabla user...")
    fix_user_fields()
    print("Proceso completado.") 