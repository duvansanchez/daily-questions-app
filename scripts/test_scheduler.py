#!/usr/bin/env python3
"""
Script para probar el scheduler y verificar que las tareas están programadas correctamente.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'daily_questions_app'))

from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import time

def test_function():
    """Función de prueba para verificar que el scheduler funciona"""
    print(f"[{datetime.now()}] ✓ Función de prueba ejecutada correctamente")

def test_scheduler():
    """
    Prueba el scheduler para verificar que funciona correctamente
    """
    print("=== Test del Scheduler ===")
    print(f"Fecha y hora: {datetime.now()}")
    print()
    
    try:
        # Crear un scheduler de prueba
        scheduler = BackgroundScheduler(timezone="America/Bogota")
        
        # Programar una tarea de prueba para ejecutarse cada 5 segundos
        scheduler.add_job(
            test_function, 
            'interval', 
            seconds=5, 
            id='test_job',
            next_run_time=datetime.now() + timedelta(seconds=2)
        )
        
        # Iniciar el scheduler
        scheduler.start()
        print("✓ Scheduler iniciado correctamente")
        
        # Mostrar trabajos programados
        jobs = scheduler.get_jobs()
        print(f"✓ Trabajos programados: {len(jobs)}")
        for job in jobs:
            print(f"   - {job.id}: {job.next_run_time}")
        
        print()
        print("Ejecutando por 15 segundos para probar...")
        print("(Deberías ver la función de prueba ejecutarse 2-3 veces)")
        print()
        
        # Esperar 15 segundos para ver las ejecuciones
        time.sleep(15)
        
        # Detener el scheduler
        scheduler.shutdown()
        print()
        print("✓ Scheduler detenido correctamente")
        print("=== Test completado exitosamente ===")
        
        return True
        
    except Exception as e:
        print(f"❌ Error durante el test del scheduler: {str(e)}")
        return False

def show_scheduler_info():
    """
    Muestra información sobre cómo funciona el scheduler en la aplicación principal
    """
    print("=== Información del Scheduler en la Aplicación ===")
    print()
    print("El scheduler está configurado para ejecutar las siguientes tareas:")
    print()
    print("1. Reset de objetivos diarios recurrentes:")
    print("   - Función: reset_objetivos_diarios_recurrentes()")
    print("   - Horario: 00:00 todos los días")
    print("   - Acción: Desmarca todos los objetivos diarios recurrentes completados")
    print()
    print("2. Verificación de proyecciones (medianoche):")
    print("   - Función: verificar_proyecciones_comienzo()")
    print("   - Horario: 00:01 todos los días")
    print("   - Acción: Envía notificaciones de objetivos con proyección para hoy")
    print()
    print("3. Verificación de proyecciones (mediodía):")
    print("   - Función: verificar_proyecciones_comienzo()")
    print("   - Horario: 12:00 todos los días")
    print("   - Acción: Envía notificaciones de objetivos con proyección para hoy")
    print()
    print("Zona horaria: America/Bogota")
    print()
    print("Para verificar que funciona en producción:")
    print("1. Inicia la aplicación Flask")
    print("2. Revisa los logs para ver: '[Scheduler] Tareas programadas:'")
    print("3. Los objetivos diarios recurrentes se resetearán automáticamente a medianoche")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--info":
        show_scheduler_info()
    else:
        test_scheduler()