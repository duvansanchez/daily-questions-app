#!/usr/bin/env python3
"""
Script para debuggear las consultas SQL de objetivos
"""

import sqlite3
import os
from datetime import datetime

def test_sql_queries():
    """Probar las consultas SQL paso a paso"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'daily_questions.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        hoy = datetime.now().date()
        user_id = 1  # Cambiar por un user_id válido
        
        print(f"🔍 Probando consultas SQL para fecha: {hoy}")
        print(f"👤 User ID: {user_id}")
        
        # Test 1: Consulta básica de objetivos
        print("\n1️⃣ Test consulta básica de objetivos:")
        cursor.execute('SELECT COUNT(*) FROM objetivos WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        print(f"   Total objetivos para user {user_id}: {count}")
        
        # Test 2: Verificar tabla objetivos_completados_log
        print("\n2️⃣ Test tabla objetivos_completados_log:")
        cursor.execute('SELECT COUNT(*) FROM objetivos_completados_log')
        count_log = cursor.fetchone()[0]
        print(f"   Total registros en log: {count_log}")
        
        # Test 3: Consulta con LEFT JOIN objetivos_saltados (original)
        print("\n3️⃣ Test consulta con objetivos_saltados:")
        try:
            cursor.execute('''
                SELECT o.id, o.titulo, 
                       CASE WHEN os.objetivo_id IS NOT NULL THEN 1 ELSE 0 END as saltado_hoy
                FROM objetivos o
                LEFT JOIN objetivos_saltados os ON o.id = os.objetivo_id AND os.user_id = o.user_id AND os.fecha_saltada = ?
                WHERE o.user_id = ?
                LIMIT 5
            ''', (hoy, user_id))
            
            rows = cursor.fetchall()
            print(f"   ✅ Consulta exitosa, {len(rows)} filas")
            for row in rows:
                print(f"      ID: {row[0]}, Título: {row[1][:30]}..., Saltado: {row[2]}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 4: Consulta con subquery para completados
        print("\n4️⃣ Test consulta con subquery completados:")
        try:
            cursor.execute('''
                SELECT o.id, o.titulo,
                       (SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END 
                        FROM objetivos_completados_log ocl 
                        WHERE ocl.objetivo_id = o.id AND ocl.user_id = o.user_id AND ocl.fecha_completado = ?) as completado_hoy
                FROM objetivos o
                WHERE o.user_id = ?
                LIMIT 5
            ''', (hoy, user_id))
            
            rows = cursor.fetchall()
            print(f"   ✅ Consulta exitosa, {len(rows)} filas")
            for row in rows:
                print(f"      ID: {row[0]}, Título: {row[1][:30]}..., Completado hoy: {row[2]}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 5: Consulta completa simplificada
        print("\n5️⃣ Test consulta completa simplificada:")
        try:
            cursor.execute('''
                SELECT o.id, o.titulo, o.completado, o.recurrente,
                       CASE WHEN os.objetivo_id IS NOT NULL THEN 1 ELSE 0 END as saltado_hoy,
                       (SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END 
                        FROM objetivos_completados_log ocl 
                        WHERE ocl.objetivo_id = o.id AND ocl.user_id = o.user_id AND ocl.fecha_completado = ?) as completado_hoy
                FROM objetivos o
                LEFT JOIN objetivos_saltados os ON o.id = os.objetivo_id AND os.user_id = o.user_id AND os.fecha_saltada = ?
                WHERE o.user_id = ?
                LIMIT 3
            ''', (hoy, hoy, user_id))
            
            rows = cursor.fetchall()
            print(f"   ✅ Consulta exitosa, {len(rows)} filas")
            for row in rows:
                print(f"      ID: {row[0]}, Título: {row[1][:30]}...")
                print(f"      Completado: {row[2]}, Recurrente: {row[3]}")
                print(f"      Saltado hoy: {row[4]}, Completado hoy: {row[5]}")
                print()
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("🎉 Tests completados")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_sql_queries()