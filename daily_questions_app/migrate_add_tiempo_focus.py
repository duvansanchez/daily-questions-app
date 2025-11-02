#!/usr/bin/env python3
"""
Migración para agregar la columna tiempo_focus a la tabla objetivos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection

def migrate_add_tiempo_focus():
    """Agregar columna tiempo_focus a la tabla objetivos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            print("🔄 Iniciando migración: Agregar columna tiempo_focus...")
            
            # Verificar si la columna ya existe
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'objetivos' 
                AND COLUMN_NAME = 'tiempo_focus'
            """)
            
            exists = cursor.fetchone()[0]
            
            if exists > 0:
                print("✅ La columna tiempo_focus ya existe en la tabla objetivos")
                return True
            
            # Agregar la columna tiempo_focus
            print("📝 Agregando columna tiempo_focus...")
            cursor.execute("""
                ALTER TABLE objetivos 
                ADD tiempo_focus INT NULL
            """)
            
            # Agregar comentario para documentar la columna
            cursor.execute("""
                EXEC sp_addextendedproperty 
                @name = N'MS_Description',
                @value = N'Tiempo en segundos dedicado al objetivo en modo focus',
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'TABLE', @level1name = N'objetivos',
                @level2type = N'COLUMN', @level2name = N'tiempo_focus'
            """)
            
            conn.commit()
            print("✅ Columna tiempo_focus agregada exitosamente")
            
            # Verificar que se agregó correctamente
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'objetivos' 
                AND COLUMN_NAME = 'tiempo_focus'
            """)
            
            column_info = cursor.fetchone()
            if column_info:
                print(f"📊 Información de la columna:")
                print(f"   - Nombre: {column_info[0]}")
                print(f"   - Tipo: {column_info[1]}")
                print(f"   - Nullable: {column_info[2]}")
            
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
            
            # Verificar estructura de la tabla
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'objetivos' 
                ORDER BY ORDINAL_POSITION
            """)
            
            columns = cursor.fetchall()
            print("\n📋 Estructura actual de la tabla objetivos:")
            print("-" * 60)
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"   {col[0]:<20} {col[1]:<15} {nullable}{default}")
            
            # Verificar específicamente la columna tiempo_focus
            tiempo_focus_exists = any(col[0] == 'tiempo_focus' for col in columns)
            
            if tiempo_focus_exists:
                print("\n✅ Migración verificada: columna tiempo_focus presente")
                return True
            else:
                print("\n❌ Error: columna tiempo_focus no encontrada")
                return False
                
    except Exception as e:
        print(f"❌ Error al verificar migración: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Migración: Agregar tiempo_focus a objetivos")
    print("=" * 50)
    
    # Ejecutar migración
    if migrate_add_tiempo_focus():
        print("\n🔍 Verificando migración...")
        if verificar_migracion():
            print("\n🎉 Migración completada exitosamente")
        else:
            print("\n⚠️ Migración ejecutada pero verificación falló")
    else:
        print("\n💥 Migración falló")