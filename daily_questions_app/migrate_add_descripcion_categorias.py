#!/usr/bin/env python3
"""
Migración para agregar columna descripcion a categorias y subcategorias
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection

def migrate_add_descripcion():
    """Agregar columna descripcion a categorias y subcategorias"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            print("🔄 Iniciando migración: Agregar columna descripcion...")
            
            # Verificar si la columna ya existe en categorias
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'categorias' 
                AND COLUMN_NAME = 'descripcion'
            """)
            
            if cursor.fetchone():
                print("✅ Columna descripcion ya existe en categorias")
            else:
                print("📝 Agregando columna descripcion a categorias...")
                cursor.execute("""
                    ALTER TABLE categorias 
                    ADD descripcion NVARCHAR(500) NULL
                """)
                print("✅ Columna descripcion agregada a categorias")
            
            # Verificar si la columna ya existe en subcategorias
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'subcategorias' 
                AND COLUMN_NAME = 'descripcion'
            """)
            
            if cursor.fetchone():
                print("✅ Columna descripcion ya existe en subcategorias")
            else:
                print("📝 Agregando columna descripcion a subcategorias...")
                cursor.execute("""
                    ALTER TABLE subcategorias 
                    ADD descripcion NVARCHAR(500) NULL
                """)
                print("✅ Columna descripcion agregada a subcategorias")
            
            conn.commit()
            print("\n✅ Migración completada exitosamente")
            
            return True
            
    except Exception as e:
        print(f"❌ Error en la migración: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verificar_migracion():
    """Verificar que la migración se aplicó correctamente"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            print("\n🔍 Verificando migración...")
            
            # Verificar categorias
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'categorias' 
                AND COLUMN_NAME = 'descripcion'
            """)
            
            col = cursor.fetchone()
            if col:
                print(f"\n📋 Tabla 'categorias':")
                print(f"   Columna: {col[0]}")
                print(f"   Tipo: {col[1]}({col[2]})")
                print(f"   Nullable: {col[3]}")
            else:
                print("❌ Columna descripcion no encontrada en categorias")
                return False
            
            # Verificar subcategorias
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'subcategorias' 
                AND COLUMN_NAME = 'descripcion'
            """)
            
            col = cursor.fetchone()
            if col:
                print(f"\n📋 Tabla 'subcategorias':")
                print(f"   Columna: {col[0]}")
                print(f"   Tipo: {col[1]}({col[2]})")
                print(f"   Nullable: {col[3]}")
            else:
                print("❌ Columna descripcion no encontrada en subcategorias")
                return False
            
            print("\n✅ Migración verificada correctamente")
            return True
                
    except Exception as e:
        print(f"❌ Error al verificar migración: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Migración: Agregar descripcion a categorías")
    print("=" * 60)
    
    # Ejecutar migración
    if migrate_add_descripcion():
        if verificar_migracion():
            print("\n🎉 Migración completada y verificada exitosamente")
        else:
            print("\n⚠️ Migración ejecutada pero verificación falló")
    else:
        print("\n💥 Migración falló")
