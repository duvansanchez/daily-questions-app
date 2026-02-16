#!/usr/bin/env python3
"""
Script para verificar categorías y subcategorías de frases
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection

def verificar_categorias():
    """Verificar categorías existentes"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar tabla categorias
            print("\n📋 CATEGORÍAS:")
            print("=" * 60)
            cursor.execute("""
                SELECT id, nombre, descripcion, activa, user_id
                FROM categorias
                ORDER BY user_id, nombre
            """)
            categorias = cursor.fetchall()
            
            if categorias:
                for cat in categorias:
                    estado = "✅ Activa" if cat[3] else "❌ Inactiva"
                    print(f"ID: {cat[0]:<5} | User: {cat[4]:<3} | {estado} | {cat[1]}")
                    if cat[2]:
                        print(f"         Descripción: {cat[2]}")
                print(f"\nTotal: {len(categorias)} categorías")
            else:
                print("⚠️ No hay categorías creadas")
            
            # Verificar tabla subcategorias
            print("\n📋 SUBCATEGORÍAS:")
            print("=" * 60)
            cursor.execute("""
                SELECT s.id, s.nombre, s.descripcion, s.activa, s.user_id, c.nombre as categoria
                FROM subcategorias s
                INNER JOIN categorias c ON s.categoria_id = c.id
                ORDER BY s.user_id, c.nombre, s.nombre
            """)
            subcategorias = cursor.fetchall()
            
            if subcategorias:
                for sub in subcategorias:
                    estado = "✅ Activa" if sub[3] else "❌ Inactiva"
                    print(f"ID: {sub[0]:<5} | User: {sub[4]:<3} | {estado} | {sub[5]} > {sub[1]}")
                    if sub[2]:
                        print(f"         Descripción: {sub[2]}")
                print(f"\nTotal: {len(subcategorias)} subcategorías")
            else:
                print("⚠️ No hay subcategorías creadas")
            
            # Verificar frases
            print("\n📋 FRASES:")
            print("=" * 60)
            cursor.execute("""
                SELECT COUNT(*) as total, user_id
                FROM frases
                GROUP BY user_id
            """)
            frases = cursor.fetchall()
            
            if frases:
                for f in frases:
                    print(f"User {f[1]}: {f[0]} frases")
            else:
                print("⚠️ No hay frases creadas")
            
            # Verificar frases con categorías
            print("\n📋 FRASES CON CATEGORÍAS:")
            print("=" * 60)
            cursor.execute("""
                SELECT f.id, f.texto, c.nombre as categoria, s.nombre as subcategoria, f.user_id
                FROM frases f
                LEFT JOIN categorias c ON f.categoria_id = c.id
                LEFT JOIN subcategorias s ON f.subcategoria_id = s.id
                ORDER BY f.user_id, c.nombre, s.nombre
            """)
            frases_cat = cursor.fetchall()
            
            if frases_cat:
                for fc in frases_cat[:10]:  # Mostrar solo las primeras 10
                    cat = fc[2] if fc[2] else "Sin categoría"
                    sub = fc[3] if fc[3] else "Sin subcategoría"
                    texto = fc[1][:50] + "..." if len(fc[1]) > 50 else fc[1]
                    print(f"User {fc[4]} | {cat} > {sub}")
                    print(f"  {texto}")
                    print()
                if len(frases_cat) > 10:
                    print(f"... y {len(frases_cat) - 10} frases más")
            else:
                print("⚠️ No hay frases con categorías")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 VERIFICACIÓN DE CATEGORÍAS Y FRASES")
    print("=" * 60)
    verificar_categorias()
