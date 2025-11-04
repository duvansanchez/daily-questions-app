#!/usr/bin/env python3
"""
Migración para crear la tabla objetivos_completados_log
Esta tabla registrará cada vez que se completa un objetivo recurrente
"""

import sqlite3
import os

def migrate_add_objetivos_completados_log():
    """Crear tabla objetivos_completados_log"""
    
    # Obtener la ruta de la base de datos
    db_path = os.path.join(os.path.dirname(__file__), 'daily_questions.db')
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la tabla ya existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='objetivos_completados_log'
        """)
        
        if cursor.fetchone():
            print("ℹ️ La tabla 'objetivos_completados_log' ya existe")
            return
            
        print("Creando tabla 'objetivos_completados_log'...")
        
        # Crear la tabla objetivos_completados_log
        cursor.execute('''
            CREATE TABLE objetivos_completados_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                objetivo_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                fecha_completado DATE NOT NULL,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
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
        print("✅ Tabla 'objetivos_completados_log' creada exitosamente")
        print("✅ Índices creados para optimizar consultas")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_add_objetivos_completados_log()