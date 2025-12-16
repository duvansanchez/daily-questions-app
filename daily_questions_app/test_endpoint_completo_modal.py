#!/usr/bin/env python3
"""
Test completo del endpoint /api/objetivos/dia/<fecha> 
para verificar que devuelve todos_los_subobjetivos correctamente
"""

import requests
import json
from datetime import datetime

def test_endpoint_modal():
    """Test del endpoint completo"""
    
    # URL del endpoint
    url = "http://localhost:5000/api/objetivos/dia/2025-12-15"
    
    print("🧪 Test del endpoint /api/objetivos/dia/2025-12-15")
    print(f"📡 URL: {url}")
    
    try:
        # Hacer la petición
        response = requests.get(url)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 401:
            print("❌ Error de autenticación - necesita login")
            return
        
        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
            return
        
        # Parsear respuesta JSON
        data = response.json()
        
        print(f"✅ Respuesta exitosa")
        print(f"📅 Fecha: {data.get('fecha')}")
        print(f"📋 Status: {data.get('status')}")
        
        # Verificar estructura de datos
        print(f"\n📊 Estructura de datos:")
        print(f"   - objetivos_creados: {len(data.get('objetivos_creados', []))}")
        print(f"   - objetivos_completados: {len(data.get('objetivos_completados', []))}")
        print(f"   - objetivos_recurrentes_pendientes: {len(data.get('objetivos_recurrentes_pendientes', []))}")
        print(f"   - subobjetivos_completados: {len(data.get('subobjetivos_completados', []))}")
        print(f"   - todos_los_subobjetivos: {len(data.get('todos_los_subobjetivos', []))}")
        
        # Verificar todos_los_subobjetivos
        todos_sub = data.get('todos_los_subobjetivos', [])
        if todos_sub:
            print(f"\n🔍 Análisis de todos_los_subobjetivos:")
            
            # Agrupar por objetivo
            por_objetivo = {}
            for sub in todos_sub:
                obj_id = sub['objetivo_id']
                if obj_id not in por_objetivo:
                    por_objetivo[obj_id] = {
                        'objetivo_titulo': sub['objetivo_titulo'],
                        'completados': [],
                        'pendientes': []
                    }
                
                if sub['completado_en_fecha']:
                    por_objetivo[obj_id]['completados'].append(sub)
                else:
                    por_objetivo[obj_id]['pendientes'].append(sub)
            
            # Mostrar resumen por objetivo
            for obj_id, info in por_objetivo.items():
                print(f"\n   🎯 Objetivo {obj_id}: {info['objetivo_titulo']}")
                print(f"      ✅ Completados: {len(info['completados'])}")
                print(f"      ⭕ Pendientes: {len(info['pendientes'])}")
                
                # Mostrar algunos ejemplos
                if info['completados']:
                    print(f"         Completados:")
                    for sub in info['completados'][:2]:  # Solo primeros 2
                        print(f"           - {sub['titulo']} ({sub['hora_completado']})")
                
                if info['pendientes']:
                    print(f"         Pendientes:")
                    for sub in info['pendientes'][:2]:  # Solo primeros 2
                        print(f"           - {sub['titulo']}")
        
        else:
            print("❌ No se encontraron todos_los_subobjetivos")
        
        print(f"\n✅ Test completado")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión - ¿Está ejecutándose la aplicación Flask?")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_endpoint_modal()