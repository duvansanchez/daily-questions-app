#!/usr/bin/env python3
"""
Script para crear objetivos de prueba para testing del modal
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
from datetime import datetime, timedelta

def crear_objetivos_prueba():
    """Crear algunos objetivos de prueba para diferentes fechas"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener el primer usuario (asumiendo que existe)
            cursor.execute("SELECT TOP 1 id FROM [user]")
            user_row = cursor.fetchone()
            if not user_row:
                print("❌ No se encontró ningún usuario en la base de datos")
                return
            
            user_id = user_row.id
            print(f"✅ Usando usuario ID: {user_id}")
            
            # Fechas para crear objetivos
            hoy = datetime.now().date()
            ayer = hoy - timedelta(days=1)
            hace_dos_dias = hoy - timedelta(days=2)
            
            objetivos_prueba = [
                # Objetivos para hoy
                {
                    'titulo': 'Revisar emails matutinos',
                    'descripcion': 'Revisar y responder emails importantes del día',
                    'categoria': 'Trabajo',
                    'prioridad': 'alta',
                    'fecha': hoy,
                    'completado': False
                },
                {
                    'titulo': 'Ejercicio 30 minutos',
                    'descripcion': 'Rutina de ejercicios cardiovasculares',
                    'categoria': 'Salud',
                    'prioridad': 'media',
                    'fecha': hoy,
                    'completado': True
                },
                {
                    'titulo': 'Leer 20 páginas',
                    'descripcion': 'Continuar leyendo libro de desarrollo personal',
                    'categoria': 'Educación',
                    'prioridad': 'baja',
                    'fecha': hoy,
                    'completado': False
                },
                
                # Objetivos para ayer
                {
                    'titulo': 'Reunión de equipo',
                    'descripcion': 'Reunión semanal con el equipo de desarrollo',
                    'categoria': 'Trabajo',
                    'prioridad': 'alta',
                    'fecha': ayer,
                    'completado': True
                },
                {
                    'titulo': 'Comprar víveres',
                    'descripcion': 'Lista de compras para la semana',
                    'categoria': 'Personal',
                    'prioridad': 'media',
                    'fecha': ayer,
                    'completado': True
                },
                
                # Objetivos para hace dos días
                {
                    'titulo': 'Estudiar Python',
                    'descripcion': 'Practicar conceptos avanzados de Python',
                    'categoria': 'Educación',
                    'prioridad': 'alta',
                    'fecha': hace_dos_dias,
                    'completado': True
                },
                {
                    'titulo': 'Llamar a familia',
                    'descripcion': 'Llamada semanal a los padres',
                    'categoria': 'Personal',
                    'prioridad': 'media',
                    'fecha': hace_dos_dias,
                    'completado': False
                }
            ]
            
            # Insertar objetivos
            for obj in objetivos_prueba:
                # Crear el objetivo
                cursor.execute("""
                    INSERT INTO objetivos (user_id, titulo, descripcion, categoria, prioridad, 
                                         fecha_creacion, completado, fecha_completado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    obj['titulo'],
                    obj['descripcion'],
                    obj['categoria'],
                    obj['prioridad'],
                    obj['fecha'],
                    obj['completado'],
                    obj['fecha'] if obj['completado'] else None
                ))
                
                print(f"✅ Creado objetivo: {obj['titulo']} ({obj['fecha']}) - {'Completado' if obj['completado'] else 'Pendiente'}")
            
            conn.commit()
            print(f"\n🎉 Se crearon {len(objetivos_prueba)} objetivos de prueba exitosamente")
            
            # Mostrar resumen por fecha
            print("\n📊 Resumen por fecha:")
            fechas = [hoy, ayer, hace_dos_dias]
            for fecha in fechas:
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN completado = 1 THEN 1 ELSE 0 END) as completados
                    FROM objetivos 
                    WHERE user_id = ? AND CAST(fecha_creacion AS DATE) = ?
                """, (user_id, fecha))
                
                row = cursor.fetchone()
                total = row.total if row else 0
                completados = row.completados if row else 0
                
                print(f"  {fecha}: {total} creados, {completados} completados")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    crear_objetivos_prueba()