#!/usr/bin/env python3
"""
Script para verificar proyecciones de comienzo de objetivos y enviar notificaciones por correo.
Este script puede ser ejecutado diariamente mediante un cron job o programador de tareas.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import pyodbc
from dotenv import load_dotenv

# Agregar el directorio actual al path para importar app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proyecciones.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    drivers = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server"
    ]
    
    for driver in drivers:
        try:
            conn_str = (
                f"DRIVER={{{driver}}};"
                "SERVER=localhost;"
                "DATABASE=DailyQuestions;"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
            )
            return pyodbc.connect(conn_str, autocommit=True)
        except Exception as e:
            logger.error(f"No se pudo conectar con {driver}: {str(e)}")
    
    raise Exception("No se pudo establecer conexión con la base de datos")

def enviar_notificacion_proyeccion_comienzo(objetivo, usuario_email):
    """
    Envía una notificación por correo cuando llega la fecha de proyección de comienzo.
    """
    try:
        # Importar aquí para evitar dependencias circulares
        from flask import Flask
        from flask_mail import Mail, Message
        
        # Crear una aplicación Flask mínima para enviar correos
        app = Flask(__name__)
        app.config['MAIL_SERVER'] = 'smtp.gmail.com'
        app.config['MAIL_PORT'] = 587
        app.config['MAIL_USE_TLS'] = True
        app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'tu_email@gmail.com')
        app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'tu_password_app')
        app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'tu_email@gmail.com')
        
        mail = Mail(app)
        
        subject = f"¡Es hora de comenzar tu objetivo: {objetivo['titulo']}!"
        
        html_body = f"""
        <html>
        <body>
            <h2>¡Hola! 👋</h2>
            <p>Hoy es la fecha que proyectaste para comenzar tu objetivo:</p>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #007bff; margin-top: 0;">{objetivo['titulo']}</h3>
                <p><strong>Descripción:</strong> {objetivo.get('descripcion', 'Sin descripción')}</p>
                <p><strong>Categoría:</strong> {objetivo.get('categoria', 'Sin categoría')}</p>
                <p><strong>Prioridad:</strong> {objetivo.get('prioridad', 'Media')}</p>
                <p><strong>Dificultad:</strong> {objetivo.get('dificultad', 'No especificada')}</p>
            </div>
            
            <p>¡Es el momento perfecto para dar el primer paso hacia tu meta!</p>
            
            <div style="margin: 30px 0;">
                <a href="http://localhost:5000/objetivos" 
                   style="background-color: #007bff; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Ver mis objetivos
                </a>
            </div>
            
            <p style="color: #6c757d; font-size: 14px;">
                Este correo fue enviado automáticamente por Daily Questions App.
            </p>
        </body>
        </html>
        """
        
        with app.app_context():
            msg = Message(
                subject=subject,
                recipients=[usuario_email],
                html=html_body
            )
            mail.send(msg)
        
        logger.info(f"Notificación enviada exitosamente a {usuario_email} para el objetivo: {objetivo['titulo']}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando notificación de proyección: {str(e)}")
        return False

def verificar_proyecciones_comienzo():
    """
    Verifica los objetivos que tienen fecha de proyección de comienzo para hoy
    y envía notificaciones por correo.
    """
    try:
        hoy = datetime.now().date()
        logger.info(f"Iniciando verificación de proyecciones para: {hoy}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar objetivos con fecha de proyección de comienzo para hoy
        cursor.execute("""
            SELECT o.id, o.titulo, o.descripcion, o.categoria, o.prioridad, o.dificultad,
                   u.username
            FROM objetivos o
            JOIN [user] u ON o.user_id = u.id
            WHERE o.fecha_proyeccion_comienzo = ?
            AND o.completado = 0
        """, (hoy,))
        
        objetivos_hoy = cursor.fetchall()
        logger.info(f"Encontrados {len(objetivos_hoy)} objetivos con proyección para hoy")
        
        notificaciones_enviadas = 0
        
        for objetivo_data in objetivos_hoy:
            objetivo = {
                'id': objetivo_data[0],
                'titulo': objetivo_data[1],
                'descripcion': objetivo_data[2],
                'categoria': objetivo_data[3],
                'prioridad': objetivo_data[4],
                'dificultad': objetivo_data[5]
            }
            
            # Usar el correo configurado en .env o un correo por defecto
            usuario_email = os.getenv('NOTIFICATION_EMAIL', 'tu_correo_destino@gmail.com')
            
            # Enviar notificación
            if enviar_notificacion_proyeccion_comienzo(objetivo, usuario_email):
                notificaciones_enviadas += 1
        
        conn.close()
        
        logger.info(f"Verificación completada. {notificaciones_enviadas} notificaciones enviadas de {len(objetivos_hoy)} objetivos.")
        return notificaciones_enviadas
        
    except Exception as e:
        logger.error(f"Error verificando proyecciones de comienzo: {str(e)}")
        return 0

if __name__ == "__main__":
    print("=== Verificador de Proyecciones de Comienzo ===")
    print(f"Fecha y hora: {datetime.now()}")
    print("Iniciando verificación...")
    
    try:
        notificaciones = verificar_proyecciones_comienzo()
        print(f"✅ Verificación completada. {notificaciones} notificaciones enviadas.")
    except Exception as e:
        print(f"❌ Error durante la verificación: {str(e)}")
        sys.exit(1) 