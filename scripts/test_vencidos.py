#!/usr/bin/env python3
"""
Test para verificar si los objetivos completados están siendo marcados como vencidos
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'daily_questions_app'))

from datetime import datetime, date, timedelta
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_connection():
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
            return pyodbc.connect(conn_str)
        except Exception as e:
            print(f"No se pudo conectar con {driver}: {str(e)}")
    raise Exception("No se pudo establecer conexión con ningún controlador ODBC")

def es_objetivo_vencido(objetivo, hoy):
    """
    Copia de la función es_objetivo_vencido del backend
    """
    # Los objetivos completados NO se consideran vencidos (ya cumplieron su propósito)
    if objetivo['completado']:
        return False
        
    # Si tiene fecha_fin explícita, usar esa
    if objetivo['fecha_fin']:
        try:
            fecha_vencimiento = datetime.strptime(objetivo['fecha_fin'], '%Y-%m-%d').date()
            return hoy > fecha_vencimiento
        except (ValueError, TypeError):
            return False
    
    # Si es recurrente, NO se considera vencido (permanece activo)
    if objetivo['recurrente']:
        return False
    
    # Objetivos NO recurrentes: vencimiento automático según categoría y fecha_creacion
    if objetivo['categoria'] and objetivo['fecha_creacion']:
        try:
            fecha_creacion = datetime.strptime(objetivo['fecha_creacion'], '%Y-%m-%d').date()
            categoria_lower = objetivo['categoria'].lower()
            
            if categoria_lower == 'diario':
                fecha_vencimiento = fecha_creacion + timedelta(days=1)
            elif categoria_lower == 'semanal':
                fecha_vencimiento = fecha_creacion + timedelta(days=7)
            elif categoria_lower == 'mensual':
                fecha_vencimiento = fecha_creacion + timedelta(days=30)
            elif categoria_lower == 'anual':
                fecha_vencimiento = fecha_creacion + timedelta(days=365)
            else:
                return False
            
            return hoy > fecha_vencimiento
        except (ValueError, TypeError):
            return False
    
    return False

def test_vencidos():
    """
    Test para verificar objetivos vencidos
    """
    print("=== Test Objetivos Vencidos ===")
    print()
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hoy = date.today()
        user_id = 3
        
        print("Obteniendo objetivos completados para verificar si están siendo marcados como vencidos:")
        cursor.execute('''
            SELECT o.id, o.titulo, o.completado, o.categoria, o.fecha_creacion, o.fecha_fin, o.recurrente
            FROM objetivos o
            WHERE o.user_id = ? AND o.completado = 1
            ORDER BY o.id
        ''', (user_id,))
        
        completados = cursor.fetchall()
        
        print(f"Total objetivos completados: {len(completados)}")
        print()
        
        vencidos_count = 0
        no_vencidos_count = 0
        
        for obj_row in completados:
            obj = {
                'id': obj_row[0],
                'titulo': obj_row[1],
                'completado': bool(obj_row[2]),
                'categoria': obj_row[3],
                'fecha_creacion': obj_row[4].strftime('%Y-%m-%d') if obj_row[4] else None,
                'fecha_fin': obj_row[5].strftime('%Y-%m-%d') if obj_row[5] else None,
                'recurrente': bool(obj_row[6])
            }
            
            vencido = es_objetivo_vencido(obj, hoy)
            
            if vencido:
                vencidos_count += 1
                print(f"  ❌ VENCIDO: ID {obj['id']} - {obj['titulo'][:40]}...")
                print(f"      Categoría: {obj['categoria']}, Fecha creación: {obj['fecha_creacion']}")
            else:
                no_vencidos_count += 1
        
        print()
        print(f"Objetivos completados VENCIDOS: {vencidos_count}")
        print(f"Objetivos completados NO VENCIDOS: {no_vencidos_count}")
        
        if vencidos_count > 0:
            print()
            print("❌ PROBLEMA ENCONTRADO:")
            print(f"   {vencidos_count} objetivos completados están siendo marcados como vencidos")
            print("   Esto significa que NO aparecen en la lista, por eso no ves el cambio de orden")
            print("   Los objetivos completados vencidos se filtran y no se muestran")
        else:
            print()
            print("✅ No hay objetivos completados marcados como vencidos")
            print("   El problema debe estar en otro lado")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_vencidos()