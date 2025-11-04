#!/usr/bin/env python3
"""
Migración para crear la tabla objetivos_completados_log en SQL Server
"""

import pyodbc
from datetime import datetime

def get_sqlserver_connection():
    """Obtiene conexión a SQL Server usando la misma configuración que la app"""
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
            )
            
            conn = pyodbc.connect(conn_str)
            print(f"✅ Conectado usando driver: {driver}")
            return conn
            
        except Exception as e:
            print(f"❌ Error con driver {driver}: {e}")
            continue
    
    raise Exception("No se pudo conectar a SQL Server")

def migrate_add_objetivos_completados_log():
    """Crear tabla objetivos_completados_log en SQL Server"""
    
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()
        
        # Verificar si la tabla ya existe
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'objetivos_completados_log'
        """)
        
        if cursor.fetchone()[0] > 0:
            print("ℹ️ La tabla 'objetivos_completados_log' ya existe")
            return
            
        print("Creando tabla 'objetivos_completados_log' en SQL Server...")
        
        # Crear la tabla objetivos_completados_log
        cursor.execute('''
            CREATE TABLE objetivos_completados_log (
                id INT IDENTITY(1,1) PRIMARY KEY,
                objetivo_id INT NOT NULL,
                user_id INT NOT NULL,
                fecha_completado DATE NOT NULL,
                fecha_creacion DATETIME2 DEFAULT GETDATE(),
                FOREIGN KEY (objetivo_id) REFERENCES objetivos (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES [user] (id) ON DELETE CASCADE,
                UNIQUE(objetivo_id, user_id, fecha_completado)
            )
        ''')
        
        # Crear índices para mejorar el rendimiento
        cursor.execute('''
            CREATE INDEX idx_objetivos_completados_log_objetivo_user 
            ON objetivos_completados_log (objetivo_id, user_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX idx_objetivos_completados_log_fecha 
            ON objetivos_completados_log (fecha_completado)
        ''')
        
        cursor.execute('''
            CREATE INDEX idx_objetivos_completados_log_user_fecha 
            ON objetivos_completados_log (user_id, fecha_completado)
        ''')
        
        conn.commit()
        print("✅ Tabla 'objetivos_completados_log' creada exitosamente en SQL Server")
        print("✅ Índices creados para optimizar consultas")
        
        # Verificar que se creó correctamente
        cursor.execute("SELECT COUNT(*) FROM objetivos_completados_log")
        print(f"✅ Tabla verificada - registros actuales: {cursor.fetchone()[0]}")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_add_objetivos_completados_log()