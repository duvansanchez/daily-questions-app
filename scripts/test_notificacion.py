#!/usr/bin/env python3
"""
Script de prueba para crear un objetivo con fecha de proyección para hoy
y probar el sistema de notificaciones.
"""

import sys
import os
from datetime import datetime, timedelta
import pyodbc
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

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
                "SERVER=localhost;"
                "DATABASE=DailyQuestions;"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
            )
            return pyodbc.connect(conn_str, autocommit=True)
        except Exception as e:
            print(f"No se pudo conectar con {driver}: {str(e)}")
    
    raise Exception("No se pudo establecer conexión con la base de datos")

def crear_objetivo_prueba():
    """Crea un objetivo de prueba con fecha de proyección para hoy"""
    try:
        hoy = datetime.now().date()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener el primer usuario (asumiendo que existe)
        cursor.execute("SELECT TOP 1 id FROM [user]")
        user_result = cursor.fetchone()
        
        if not user_result:
            print("❌ No hay usuarios en la base de datos. Crea un usuario primero.")
            return False
        
        user_id = user_result[0]
        
        # Crear objetivo de prueba
        objetivo_data = {
            'titulo': 'Objetivo de Prueba - Notificaciones',
            'descripcion': 'Este es un objetivo de prueba para verificar el sistema de notificaciones por correo.',
            'prioridad': 'alta',
            'categoria': 'diario',
            'estado': 'pendiente',
            'fecha_proyeccion_comienzo': hoy,
            'dificultad': 3,
            'etiquetas': 'prueba, notificaciones, correo',
            'recompensa': 'Verificar que funciona el sistema',
            'notas_adicionales': 'Objetivo creado automáticamente para probar notificaciones'
        }
        
        cursor.execute("""
            INSERT INTO objetivos (
                user_id, titulo, descripcion, prioridad, categoria, completado, 
                fecha_creacion, es_padre, estado, fecha_proyeccion_comienzo, 
                dificultad, etiquetas, recompensa, notas_adicionales, recurrente, frecuencia
            ) VALUES (?, ?, ?, ?, ?, 0, GETDATE(), 0, ?, ?, ?, ?, ?, ?, 0, NULL)
        """, (
            user_id, objetivo_data['titulo'], objetivo_data['descripcion'],
            objetivo_data['prioridad'], objetivo_data['categoria'],
            objetivo_data['estado'], objetivo_data['fecha_proyeccion_comienzo'],
            objetivo_data['dificultad'], objetivo_data['etiquetas'],
            objetivo_data['recompensa'], objetivo_data['notas_adicionales']
        ))
        
        conn.close()
        
        print(f"✅ Objetivo de prueba creado exitosamente:")
        print(f"   - Título: {objetivo_data['titulo']}")
        print(f"   - Fecha de proyección: {objetivo_data['fecha_proyeccion_comienzo']}")
        print(f"   - Usuario ID: {user_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando objetivo de prueba: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Creando Objetivo de Prueba ===")
    print(f"Fecha actual: {datetime.now().date()}")
    
    if crear_objetivo_prueba():
        print("\n🎯 Ahora puedes probar el sistema de notificaciones:")
        print("1. Ejecuta: python verificar_proyecciones.py")
        print("2. Verifica tu correo electrónico")
        print("3. El objetivo aparecerá en la aplicación web")
    else:
        print("\n❌ No se pudo crear el objetivo de prueba")
        sys.exit(1) 