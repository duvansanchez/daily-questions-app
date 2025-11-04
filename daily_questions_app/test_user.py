#!/usr/bin/env python3
"""
Script para verificar y crear usuarios de prueba
"""
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server", 
        "SQL Server"
    ]
    
    for driver in drivers:
        try:
            conn_str = (
                f"DRIVER={{{driver}}};"
                "SERVER=DESKTOP-2MR0PJ6;"
                "DATABASE=DailyQuestions;"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
                "Connection Timeout=30;"
                "charset=UTF-8;"
                "encoding=UTF-8;"
                "MARS_Connection=yes;"
            )
            conn = pyodbc.connect(conn_str)
            print(f"✅ Conectado usando driver: {driver}")
            return conn
        except Exception as e:
            print(f"❌ Error con driver {driver}: {e}")
            continue
    
    raise Exception("No se pudo conectar a la base de datos")

def verificar_usuarios():
    """Verifica qué usuarios existen en la base de datos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password FROM [user]")
            usuarios = cursor.fetchall()
            
            print("\n📋 Usuarios existentes:")
            print("-" * 50)
            for usuario in usuarios:
                print(f"ID: {usuario[0]}, Username: {usuario[1]}")
            
            return usuarios
    except Exception as e:
        print(f"❌ Error al verificar usuarios: {e}")
        return []

def crear_usuario_prueba():
    """Crea un usuario de prueba"""
    username = "test"
    password = "123456"  # Contraseña simple para pruebas
    email = "test@test.com"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si el usuario ya existe
            cursor.execute("SELECT id FROM [user] WHERE username = ?", (username,))
            if cursor.fetchone():
                print(f"⚠️ El usuario '{username}' ya existe")
                return False
            
            # Crear el usuario
            password_hash = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO [user] (username, password)
                VALUES (?, ?)
            """, (username, password_hash))
            
            conn.commit()
            print(f"✅ Usuario '{username}' creado exitosamente")
            print(f"   Contraseña: {password}")
            return True
            
    except Exception as e:
        print(f"❌ Error al crear usuario: {e}")
        return False

def verificar_password(username, password):
    """Verifica si la contraseña es correcta para un usuario"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM [user] WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if result:
                stored_hash = result[0]
                is_valid = check_password_hash(stored_hash, password)
                print(f"🔐 Contraseña para '{username}': {'✅ Válida' if is_valid else '❌ Inválida'}")
                return is_valid
            else:
                print(f"❌ Usuario '{username}' no encontrado")
                return False
                
    except Exception as e:
        print(f"❌ Error al verificar contraseña: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verificando usuarios en la base de datos...")
    usuarios = verificar_usuarios()
    
    if not usuarios:
        print("\n📝 No hay usuarios. Creando usuario de prueba...")
        crear_usuario_prueba()
    else:
        print(f"\n✅ Se encontraron {len(usuarios)} usuarios")
        
        # Verificar contraseñas comunes para el usuario duvan
        if any(u[1] == 'duvan' for u in usuarios):
            print("\n🔐 Probando contraseñas comunes para 'duvan':")
            passwords_to_try = ['123456', 'duvan', 'password', 'admin', '12345']
            for pwd in passwords_to_try:
                if verificar_password('duvan', pwd):
                    print(f"🎉 ¡Contraseña encontrada! Usuario: duvan, Contraseña: {pwd}")
                    break