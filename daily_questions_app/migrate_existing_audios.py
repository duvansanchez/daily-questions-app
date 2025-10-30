#!/usr/bin/env python3
"""
Script para migrar audios existentes del sistema de archivos a la base de datos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_existing_audios():
    """Migrar audios existentes del filesystem a la base de datos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener audios que tienen archivo_url pero no contenido_binario
            cursor.execute('''
                SELECT id, user_id, archivo_url, archivo_nombre
                FROM audios 
                WHERE archivo_url IS NOT NULL 
                AND (contenido_binario IS NULL OR LEN(contenido_binario) = 0)
            ''')
            
            audios_to_migrate = cursor.fetchall()
            
            if not audios_to_migrate:
                logger.info("✅ No hay audios para migrar")
                return
            
            logger.info(f"📁 Encontrados {len(audios_to_migrate)} audios para migrar")
            
            migrated_count = 0
            error_count = 0
            
            for audio_id, user_id, archivo_url, archivo_nombre in audios_to_migrate:
                try:
                    # Construir ruta del archivo físico
                    if archivo_url.startswith('/static/uploads/audios/'):
                        # Remover el prefijo para obtener la ruta relativa
                        relative_path = archivo_url.replace('/static/uploads/audios/', '')
                        file_path = os.path.join(
                            os.path.dirname(os.path.abspath(__file__)),
                            'static', 'uploads', 'audios', relative_path
                        )
                    else:
                        logger.warning(f"⚠️  Audio {audio_id}: URL no reconocida: {archivo_url}")
                        continue
                    
                    # Verificar si el archivo existe
                    if not os.path.exists(file_path):
                        logger.warning(f"⚠️  Audio {audio_id}: Archivo no encontrado: {file_path}")
                        error_count += 1
                        continue
                    
                    # Leer contenido binario
                    with open(file_path, 'rb') as f:
                        contenido_binario = f.read()
                    
                    # Determinar tipo MIME basado en extensión
                    file_ext = os.path.splitext(archivo_nombre)[1].lower()
                    tipo_mime_map = {
                        '.mp3': 'audio/mpeg',
                        '.wav': 'audio/wav',
                        '.m4a': 'audio/mp4',
                        '.ogg': 'audio/ogg'
                    }
                    tipo_mime = tipo_mime_map.get(file_ext, 'audio/mpeg')
                    
                    # Actualizar registro en base de datos
                    cursor.execute('''
                        UPDATE audios 
                        SET contenido_binario = ?, tipo_mime = ?
                        WHERE id = ?
                    ''', (contenido_binario, tipo_mime, audio_id))
                    
                    logger.info(f"✅ Audio {audio_id} migrado ({len(contenido_binario)} bytes)")
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error migrando audio {audio_id}: {str(e)}")
                    error_count += 1
            
            conn.commit()
            
            logger.info(f"🎉 Migración completada:")
            logger.info(f"   ✅ Migrados: {migrated_count}")
            logger.info(f"   ❌ Errores: {error_count}")
            
            if migrated_count > 0:
                logger.info("💡 Los archivos físicos pueden eliminarse ahora si lo deseas")
                
    except Exception as e:
        logger.error(f"❌ Error en migración: {str(e)}")
        raise

if __name__ == '__main__':
    migrate_existing_audios()