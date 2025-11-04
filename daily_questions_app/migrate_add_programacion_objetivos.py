#!/usr/bin/env python3
"""
Migración para agregar campos de programación de objetivos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection

def migrate_add_programacion_objetivos():
    """Agregar campos para programación de objetivos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            print("🔄 Iniciando migración: Agregar campos de programación...")
            
            # Verificar si las columnas ya existen
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'objetivos' 
                AND COLUMN_NAME IN ('fecha_programada', 'programado_para')
            """)
            
            existing_columns = [row[0] for row in cursor.fetchall()]
            
            # Agregar fecha_programada si no existe
            if 'fecha_programada' not in existing_columns:
                print("📝 Agregando columna fecha_programada...")
                cursor.execute("""
                    ALTER TABLE objetivos 
                    ADD fecha_programada DATE NULL
                """)
                
                # Agregar comentario
                cursor.execute("""
                    EXEC sp_addextendedproperty 
                    @name = N'MS_Description',
                    @value = N'Fecha para la cual está programado el objetivo (NULL = hoy)',
                    @level0type = N'SCHEMA', @level0name = N'dbo',
                    @level1type = N'TABLE', @level1name = N'objetivos',
                    @level2type = N'COLUMN', @level2name = N'fecha_programada'
                """)
                print("✅ Columna fecha_programada agregada")
            else:
                print("✅ Columna fecha_programada ya existe")
            
            # Agregar programado_para si no existe
            if 'programado_para' not in existing_columns:
                print("📝 Agregando columna programado_para...")
                cursor.execute("""
                    ALTER TABLE objetivos 
                    ADD programado_para NVARCHAR(20) NULL
                """)
                
                # Agregar comentario
                cursor.execute("""
                    EXEC sp_addextendedproperty 
                    @name = N'MS_Description',
                    @value = N'Indica para cuándo está programado: hoy, mañana, fecha_especifica',
                    @level0type = N'SCHEMA', @level0name = N'dbo',
                    @level1type = N'TABLE', @level1name = N'objetivos',
                    @level2type = N'COLUMN', @level2name = N'programado_para'
                """)
                print("✅ Columna programado_para agregada")
            else:
                print("✅ Columna programado_para ya existe")
            
            conn.commit()
            print("✅ Migración completada exitosamente")
            
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
            
            # Verificar las nuevas columnas
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'objetivos' 
                AND COLUMN_NAME IN ('fecha_programada', 'programado_para')
                ORDER BY COLUMN_NAME
            """)
            
            columns = cursor.fetchall()
            print("\n📋 Nuevas columnas de programación:")
            print("-" * 50)
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"   {col[0]:<20} {col[1]:<15} {nullable}{default}")
            
            # Verificar que ambas columnas existen
            column_names = [col[0] for col in columns]
            required_columns = ['fecha_programada', 'programado_para']
            
            missing = [col for col in required_columns if col not in column_names]
            
            if not missing:
                print("\n✅ Migración verificada: todas las columnas presentes")
                return True
            else:
                print(f"\n❌ Error: columnas faltantes: {missing}")
                return False
                
    except Exception as e:
        print(f"❌ Error al verificar migración: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Migración: Agregar programación de objetivos")
    print("=" * 50)
    
    # Ejecutar migración
    if migrate_add_programacion_objetivos():
        print("\n🔍 Verificando migración...")
        if verificar_migracion():
            print("\n🎉 Migración completada exitosamente")
        else:
            print("\n⚠️ Migración ejecutada pero verificación falló")
    else:
        print("\n💥 Migración falló")