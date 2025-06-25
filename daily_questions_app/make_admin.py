import pyodbc

def make_admin(username):
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-PIDFCJG;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print(f"Actualizando permisos de administrador para el usuario: {username}")
        
        # Actualizar el usuario a administrador
        cursor.execute('''
            UPDATE [user] 
            SET is_admin = 1 
            WHERE username = ?
        ''', (username,))
        
        if cursor.rowcount == 0:
            print(f"Error: No se encontró el usuario '{username}'")
        else:
            conn.commit()
            print(f"¡Usuario '{username}' actualizado a administrador exitosamente!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Uso: python make_admin.py <nombre_de_usuario>")
        sys.exit(1)
    
    username = sys.argv[1]
    print(f"Iniciando actualización de permisos para: {username}")
    make_admin(username)
    print("Proceso completado. Por favor, cierra sesión y vuelve a iniciar para que los cambios surtan efecto.")
