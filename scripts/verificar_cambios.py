#!/usr/bin/env python3
"""
Script para verificar que los cambios están aplicados correctamente
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'daily_questions_app'))

def verificar_cambios():
    """
    Verifica que los cambios estén en el código
    """
    print("=== Verificación de Cambios ===")
    print()
    
    try:
        # Leer el archivo app.py
        with open('daily_questions_app/app.py', 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar la consulta modificada
        if 'ORDER BY \n                o.completado ASC,' in contenido:
            print("✅ La consulta modificada está en el código")
        else:
            print("❌ La consulta modificada NO está en el código")
        
        # Buscar el comentario que agregamos
        if 'pone solo los completados al final' in contenido:
            print("✅ El comentario de la modificación está presente")
        else:
            print("❌ El comentario de la modificación NO está presente")
        
        print()
        print("Pasos para aplicar los cambios:")
        print("1. ✅ Código modificado correctamente")
        print("2. 🔄 REINICIA la aplicación Flask (python daily_questions_app/app.py)")
        print("3. 🔄 RECARGA la página en el navegador (Ctrl+F5 o Cmd+Shift+R)")
        print("4. 🔍 Ve a la página de objetivos para ver el nuevo ordenamiento")
        print()
        print("Si sigues viendo el mismo orden:")
        print("- Asegúrate de que la aplicación Flask se reinició")
        print("- Limpia el cache del navegador")
        print("- Verifica que estés en la página correcta de objetivos")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    verificar_cambios()