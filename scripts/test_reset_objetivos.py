#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento del reset automático de objetivos diarios recurrentes.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'daily_questions_app'))

from datetime import datetime
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Obtiene una conexión a la base de datos con manejo de contexto"""
    class ConnectionContext:
        def __init__(self):
            self.conn = None
            
        def __enter__(self):
            # Intentar con ODBC 18 primero, luego 17, luego el genérico
            drivers = [
                "ODBC Driver 18 for SQL Server",
                "ODBC Driver 17 for SQL Server",
                "SQL Server"  # Último recurso
            ]
            
            last_error = None
            
            for driver in drivers:
                try:
                    # Configuración de conexión actualizada
                    conn_str = (
                        f"DRIVER={{{driver}}};"
                        "SERVER=DESKTOP-2MR0PJ6;"  # Solo el nombre del servidor
                        "DATABASE=DailyQuestions;"
                        "Trusted_Connection=yes;"  # Usando autenticación de Windows
                        "TrustServerCertificate=yes;"
                        "Connection Timeout=30;"
                        "charset=UTF-8;"
                        "encoding=UTF-8;"
                        "MARS_Connection=yes;"
                        "ApplicationIntent=ReadWrite;"
                    )
                    self.conn = pyodbc.connect(conn_str, autocommit=False)
                    
                    # Configurar el cursor para mejor manejo de errores
                    cursor = self.conn.cursor()
                    cursor.execute("SET ARITHABORT ON")
                    cursor.execute("SET ANSI_WARNINGS ON")
                    cursor.execute("SET ANSI_PADDING ON")
                    cursor.execute("SET ANSI_NULLS ON")
                    cursor.execute("SET CONCAT_NULL_YIELDS_NULL ON")
                    cursor.execute("SET QUOTED_IDENTIFIER ON")
                    cursor.execute("SET NOCOUNT ON")
                    return self.conn
                except Exception as e:
                    last_error = e
                    print(f"No se pudo conectar con {driver}: {str(e)}")
            
            # Si llegamos aquí, todas las conexiones fallaron
            error_msg = "No se pudo establecer conexión con ningún controlador ODBC disponible"
            print(error_msg)
            if last_error:
                print(f"Último error: {str(last_error)}")
            raise Exception(error_msg)
                
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.conn:
                if exc_type is not None:  # Si hubo un error
                    print(f"Error en la conexión: {str(exc_val)}")
                    self.conn.rollback()
                else:
                    self.conn.commit()
                self.conn.close()
    
    return ConnectionContext()

def test_reset_objetivos_diarios():
    """
    Prueba la función de reset de objetivos diarios recurrentes
    """
    print("=== Test Reset Objetivos Diarios Recurrentes ===")
    print(f"Fecha y hora: {datetime.now()}")
    print()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Mostrar estado actual de objetivos diarios recurrentes
            print("1. Estado actual de objetivos diarios recurrentes:")
            cursor.execute("""
                SELECT id, titulo, completado, fecha_completado, user_id
                FROM objetivos 
                WHERE LOWER(COALESCE(categoria,'')) = 'diario'
                AND COALESCE(recurrente, 0) = 1
                AND COALESCE(estado,'') <> 'histórico'
                ORDER BY user_id, titulo
            """)
            
            objetivos_antes = cursor.fetchall()
            if objetivos_antes:
                for obj in objetivos_antes:
                    estado = "✓ Completado" if obj[2] else "○ Pendiente"
                    fecha_comp = f" ({obj[3]})" if obj[3] else ""
                    print(f"   ID {obj[0]} - User {obj[4]} - {obj[1]} - {estado}{fecha_comp}")
            else:
                print("   No se encontraron objetivos diarios recurrentes")
            
            print()
            
            # 2. Ejecutar el reset
            print("2. Ejecutando reset de objetivos diarios recurrentes...")
            cursor.execute("""
                UPDATE objetivos 
                SET completado = 0, fecha_completado = NULL
                WHERE LOWER(COALESCE(categoria,'')) = 'diario'
                AND COALESCE(recurrente, 0) = 1
                AND completado = 1
                AND COALESCE(estado,'') <> 'histórico'
            """)
            
            objetivos_desmarcados = cursor.rowcount
            conn.commit()
            
            print(f"   ✓ {objetivos_desmarcados} objetivos desmarcados")
            print()
            
            # 3. Mostrar estado después del reset
            print("3. Estado después del reset:")
            cursor.execute("""
                SELECT id, titulo, completado, fecha_completado, user_id
                FROM objetivos 
                WHERE LOWER(COALESCE(categoria,'')) = 'diario'
                AND COALESCE(recurrente, 0) = 1
                AND COALESCE(estado,'') <> 'histórico'
                ORDER BY user_id, titulo
            """)
            
            objetivos_despues = cursor.fetchall()
            if objetivos_despues:
                for obj in objetivos_despues:
                    estado = "✓ Completado" if obj[2] else "○ Pendiente"
                    fecha_comp = f" ({obj[3]})" if obj[3] else ""
                    print(f"   ID {obj[0]} - User {obj[4]} - {obj[1]} - {estado}{fecha_comp}")
            else:
                print("   No se encontraron objetivos diarios recurrentes")
            
            print()
            print("=== Test completado exitosamente ===")
            
    except Exception as e:
        print(f"❌ Error durante el test: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    test_reset_objetivos_diarios()