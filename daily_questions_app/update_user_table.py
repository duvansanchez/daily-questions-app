import pyodbc

def update_user_table():
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-32COF63;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Verificando si la columna is_admin existe...")
        
        # Verificar si la columna ya existe
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                          WHERE TABLE_NAME = 'user' AND COLUMN_NAME = 'is_admin')
            BEGIN
                ALTER TABLE [user] ADD is_admin BIT DEFAULT 0;
                PRINT 'Columna is_admin agregada a la tabla user.';
            END
            ELSE
                PRINT 'La columna is_admin ya existe en la tabla user.';
        ''')
        
        conn.commit()
        print("Verificación y actualización completadas con éxito.")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    print("Actualizando la estructura de la tabla user...")
    update_user_table()
    print("Proceso completado. Por favor, inicia sesión nuevamente para que los cambios surtan efecto.")
