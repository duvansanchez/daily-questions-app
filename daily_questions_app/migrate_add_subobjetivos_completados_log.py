#!/usr/bin/env python3
"""
Migración para crear tabla subobjetivos_completados_log
Registra cada vez que se completa un subobjetivo en una fecha específica
"""

import pyodbc
import sys
import os

# Agregar el directorio padre al path para importar la configuración
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=DESKTOP-2MR0PJ6;"
        "DATABASE=DailyQuestions;"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

def migrate():
    """Ejecuta la migración"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔄 Iniciando migración para crear tabla subobjetivos_completados_log...")
        
        # Verificar si la tabla ya existe
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'subobjetivos_completados_log'
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists > 0:
            print("✅ La tabla subobjetivos_completados_log ya existe")
        else:
            # Crear la tabla subobjetivos_completados_log
            cursor.execute('''
                CREATE TABLE subobjetivos_completados_log (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    subobjetivo_id INT NOT NULL,
                    objetivo_id INT NOT NULL,
                    user_id INT NOT NULL,
                    fecha_completado DATE NOT NULL,
                    fecha_creacion DATETIME2 DEFAULT GETDATE(),
                    FOREIGN KEY (subobjetivo_id) REFERENCES subobjetivos (id) ON DELETE NO ACTION,
                    FOREIGN KEY (objetivo_id) REFERENCES objetivos (id) ON DELETE NO ACTION,
                    FOREIGN KEY (user_id) REFERENCES [user] (id) ON DELETE NO ACTION,
                    UNIQUE(subobjetivo_id, user_id, fecha_completado)
                )
            ''')
            
            print("✅ Tabla subobjetivos_completados_log creada")
            
            # Crear índices para mejorar el rendimiento
            cursor.execute('''
                CREATE INDEX idx_subobjetivos_completados_log_subobjetivo_user 
                ON subobjetivos_completados_log (subobjetivo_id, user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX idx_subobjetivos_completados_log_objetivo_user 
                ON subobjetivos_completados_log (objetivo_id, user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX idx_subobjetivos_completados_log_fecha 
                ON subobjetivos_completados_log (fecha_completado)
            ''')
            
            print("✅ Índices creados para subobjetivos_completados_log")
        
        conn.commit()
        conn.close()
        
        print("🎉 Migración completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    migrate()