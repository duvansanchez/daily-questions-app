#!/usr/bin/env python3
"""
Test del endpoint HTTP completo
"""

import requests
import json
from datetime import datetime

def test_endpoint_http(fecha):
    """Probar el endpoint HTTP completo"""
    try:
        url = f"http://localhost:5000/api/objetivos/dia/{fecha}"
        print(f"🌐 Probando: {url}")
        
        # Hacer la petición
        response = requests.get(url, timeout=10)
        
        print(f"📊 Status: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Respuesta exitosa:")
            print(f"  - Status: {data.get('status', 'N/A')}")
            print(f"  - Fecha: {data.get('fecha', 'N/A')}")
            
            if 'resumen' in data:
                resumen = data['resumen']
                print(f"  - Total creados: {resumen.get('total_creados', 0)}")
                print(f"  - Total completados: {resumen.get('total_completados', 0)}")
            
            if 'objetivos_creados' in data:
                print(f"  - Objetivos creados: {len(data['objetivos_creados'])} items")
                for i, obj in enumerate(data['objetivos_creados'][:3]):  # Mostrar solo los primeros 3
                    print(f"    {i+1}. {obj.get('titulo', 'Sin título')}")
            
            if 'objetivos_completados' in data:
                print(f"  - Objetivos completados: {len(data['objetivos_completados'])} items")
                for i, obj in enumerate(data['objetivos_completados'][:3]):  # Mostrar solo los primeros 3
                    print(f"    {i+1}. {obj.get('titulo', 'Sin título')}")
            
            return True
            
        elif response.status_code == 401:
            print("❌ Error 401: No autenticado")
            print("💡 Esto es normal - el endpoint requiere autenticación")
            return False
            
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión: ¿Está el servidor ejecutándose?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Test del endpoint HTTP completo")
    print("=" * 50)
    
    # Fechas para probar
    fechas = [
        '2025-11-01',
        '2025-10-31', 
        '2025-10-30',
        '2024-10-31'  # Fecha sin datos
    ]
    
    for fecha in fechas:
        print(f"\n📅 Probando fecha: {fecha}")
        print("-" * 30)
        resultado = test_endpoint_http(fecha)
        if not resultado:
            print("⚠️  Endpoint no accesible sin autenticación")
        print()
    
    print("✅ Test completado")