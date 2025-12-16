#!/usr/bin/env python3
"""
Script para probar el endpoint de subobjetivos completados
"""

import requests
import json
from datetime import datetime

def test_endpoint():
    """Prueba el endpoint de objetivos del día con subobjetivos"""
    
    # URL base (ajusta según tu configuración)
    base_url = "http://localhost:5000"
    
    # Fecha de prueba (hoy)
    fecha = datetime.now().strftime('%Y-%m-%d')
    
    print(f"🧪 Probando endpoint para fecha: {fecha}")
    
    try:
        # 1. Probar endpoint principal
        url = f"{base_url}/api/objetivos/dia/{fecha}"
        print(f"📡 GET {url}")
        
        response = requests.get(url)
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Respuesta exitosa")
            
            # Mostrar estructura de respuesta
            print(f"📋 Status: {data.get('status')}")
            print(f"📅 Fecha: {data.get('fecha')}")
            
            if 'resumen' in data:
                resumen = data['resumen']
                print("📊 Resumen:")
                for key, value in resumen.items():
                    print(f"   - {key}: {value}")
            
            # Verificar subobjetivos completados
            if 'subobjetivos_completados' in data:
                subs = data['subobjetivos_completados']
                print(f"🎯 Subobjetivos completados: {len(subs)}")
                
                for sub in subs:
                    print(f"   ✅ {sub['titulo']} ({sub['objetivo_titulo']}) - {sub.get('hora_completado', 'N/A')}")
            else:
                print("❌ No se encontró 'subobjetivos_completados' en la respuesta")
                print("📋 Claves disponibles:", list(data.keys()))
        
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📄 Respuesta: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión. ¿Está corriendo el servidor Flask?")
        print("💡 Ejecuta: python daily_questions_app/app.py")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_endpoint()