#!/usr/bin/env python3
"""
Script para crear la tabla de frases inspiracionales
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from daily_questions_app.app import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_frases_table():
    """Crear la tabla de frases"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Crear tabla de frases
            cursor.execute('''
                CREATE TABLE frases (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INT NOT NULL,
                    texto NVARCHAR(1000) NOT NULL,
                    autor NVARCHAR(200),
                    categoria NVARCHAR(50) NOT NULL,
                    notas NVARCHAR(500),
                    total_repasos INT DEFAULT 0,
                    ultima_vez DATETIME,
                    fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
                    FOREIGN KEY (user_id) REFERENCES [user](id) ON DELETE CASCADE
                )
            ''')
            
            # Crear índices para mejor rendimiento
            cursor.execute('CREATE INDEX IX_frases_user_id ON frases(user_id)')
            cursor.execute('CREATE INDEX IX_frases_categoria ON frases(categoria)')
            cursor.execute('CREATE INDEX IX_frases_ultima_vez ON frases(ultima_vez)')
            
            conn.commit()
            logger.info("Tabla 'frases' creada exitosamente")
            
            # Insertar algunas frases de ejemplo
            frases_ejemplo = [
                {
                    'texto': 'El éxito no es la clave de la felicidad. La felicidad es la clave del éxito.',
                    'autor': 'Albert Schweitzer',
                    'categoria': 'exito'
                },
                {
                    'texto': 'No esperes por el momento perfecto, toma el momento y hazlo perfecto.',
                    'autor': None,
                    'categoria': 'motivacion'
                },
                {
                    'texto': 'La persistencia puede cambiar el fracaso en un logro extraordinario.',
                    'autor': 'Matt Biondi',
                    'categoria': 'perseverancia'
                },
                {
                    'texto': 'El conocimiento habla, pero la sabiduría escucha.',
                    'autor': 'Jimi Hendrix',
                    'categoria': 'sabiduria'
                },
                {
                    'texto': 'No se trata de ser perfecto, se trata de ser mejor que ayer.',
                    'autor': None,
                    'categoria': 'crecimiento'
                }
            ]
            
            # Obtener el primer usuario para las frases de ejemplo
            cursor.execute('SELECT TOP 1 id FROM [user] ORDER BY id')
            user_result = cursor.fetchone()
            
            if user_result:
                user_id = user_result[0]
                
                for frase in frases_ejemplo:
                    cursor.execute('''
                        INSERT INTO frases (user_id, texto, autor, categoria, fecha_creacion)
                        VALUES (?, ?, ?, ?, GETDATE())
                    ''', (
                        user_id,
                        frase['texto'],
                        frase['autor'],
                        frase['categoria']
                    ))
                
                conn.commit()
                logger.info(f"Insertadas {len(frases_ejemplo)} frases de ejemplo")
            
    except Exception as e:
        logger.error(f"Error creando tabla de frases: {str(e)}")
        raise

if __name__ == '__main__':
    create_frases_table()
    print("¡Tabla de frases creada exitosamente!")