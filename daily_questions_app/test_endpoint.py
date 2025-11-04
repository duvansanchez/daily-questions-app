#!/usr/bin/env python3
"""
Script para probar el endpoint de actualización de subobjetivos
"""

import requests
import json

def test_endpoint():
    """Prueba el endpoint de actualización"""
    
    # Configuración
    base_url = "http://localhost:5000"
    
    # Primero necesitamos hacer login (esto es solo para prueba)
    # En producción usarías las credenciales reales
    
    # Obtener un subobjetivo existente para probar
    print("🔍 Probando endpoint de actualización de subobjetivos...")
    
    # Datos de prueba
    subobjetivo_id = 2018  # ID de ejemplo de la verificación anterior
    test_data = {
        "tiempo_focus": 120  # 2 minutos en segundos
    }
    
    print(f"📤 Enviando PATCH a /api/subobjetivos/{subobjetivo_id}")
    print(f"📦 Datos: {json.dumps(test_data, indent=2)}")
    
    # Nota: Este test no funcionará sin autenticación
    # Es solo para mostrar cómo debería ser la petición
    print("⚠️  Nota: Este test requiere autenticación activa en el navegador")
    print("💡 Para probar manualmente:")
    print(f"   1. Abre la consola del navegador en {base_url}")
    print("   2. Ejecuta:")
    print(f"""
    fetch('/api/subobjetivos/{subobjetivo_id}', {{
        method: 'PATCH',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({json.dumps(test_data)})
    }})
    .then(r => r.json())
    .then(console.log)
    .catch(console.error);
    """)

if __name__ == "__main__":
    test_endpoint()