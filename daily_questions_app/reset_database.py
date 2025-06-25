import pyodbc

def reset_database():
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-PIDFCJG;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Eliminando todas las respuestas...")
        cursor.execute("DELETE FROM response")
        
        print("Eliminando todas las preguntas...")
        cursor.execute("DELETE FROM question")
        
        print("Eliminando todos los usuarios...")
        cursor.execute("DELETE FROM [user]")
        
        # Reiniciar los contadores de identidad
        cursor.execute("DBCC CHECKIDENT ('response', RESEED, 0)")
        cursor.execute("DBCC CHECKIDENT ('question', RESEED, 0)")
        cursor.execute("DBCC CHECKIDENT ('[user]', RESEED, 0)")
        
        conn.commit()
        print("Base de datos reiniciada exitosamente. Todos los usuarios, preguntas y respuestas han sido eliminados.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    print("¡ADVERTENCIA! Esto eliminará TODOS los datos de la base de datos.")
    print("Ejecutando limpieza de la base de datos...")
    reset_database()
