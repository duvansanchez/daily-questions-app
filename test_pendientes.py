#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar el cálculo de pendientes por día
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pendientes_logic():
    """Probar la lógica de cálculo de pendientes"""

    # Simular datos de prueba
    inicio = datetime(2024, 11, 1)  # Mes actual
    fin = datetime(2024, 12, 1)

    # Simular current_user
    current_user = Mock()
    current_user.id = 1

    # Simular cursor de base de datos
    cursor = Mock()

    # Configurar respuestas simuladas del cursor
    cursor.fetchone.side_effect = [
        (3,),  # recurrentes_pendientes para día 1
        (0,),  # normales_pendientes para día 1
        (2,),  # recurrentes_pendientes para día 2
        (1,),  # normales_pendientes para día 2
        (1,),  # recurrentes_pendientes para día 3
        (0,),  # normales_pendientes para día 3
        # ... continuar para otros días con 0
    ] + [(0,), (0,)] * 28  # Rellenar con ceros para los días restantes

    # Simular execute calls counter
    execute_calls = []

    def mock_execute(query, params):
        execute_calls.append((query.strip(), params))
        return None

    cursor.execute = mock_execute

    # Ejecutar la lógica del bucle
    pendientes = {}
    dia_actual_loop = inicio.date()
    call_index = 0

    while dia_actual_loop < fin.date():
        fecha_dia = dia_actual_loop
        dia_str = str(fecha_dia.day)

        # Solo calcular para días pasados o hoy
        if fecha_dia <= datetime.now().date():
            # 3a. Objetivos recurrentes no completados ese día
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM objetivos o
                LEFT JOIN objetivos_completados_log ocl ON o.id = ocl.objetivo_id
                    AND ocl.user_id = o.user_id
                    AND CONVERT(date, ocl.fecha_completado) = ?
                WHERE o.user_id = ?
                  AND o.recurrente = 1
                  AND o.estado != 'histórico'
                  AND ocl.id IS NULL
                """,
                (fecha_dia, current_user.id)
            )
            recurrentes_pendientes = cursor.fetchone()[0]

            # 3b. Objetivos normales creados ese día no completados
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM objetivos
                WHERE user_id = ?
                  AND CAST(fecha_creacion AS DATE) = ?
                  AND (recurrente = 0 OR recurrente IS NULL)
                  AND completado = 0
                """,
                (current_user.id, fecha_dia)
            )
            normales_pendientes = cursor.fetchone()[0]

            total_pendientes_dia = recurrentes_pendientes + normales_pendientes
            if total_pendientes_dia > 0:
                pendientes[dia_str] = total_pendientes_dia

        dia_actual_loop += timedelta(days=1)

    print(f"Total de llamadas a execute: {len(execute_calls)}")
    print(f"Días con pendientes: {len(pendientes)}")
    print(f"Pendientes por día: {pendientes}")

    # Verificar que se hicieron las llamadas correctas
    expected_days = (datetime.now().date() - inicio.date()).days + 1
    expected_calls = expected_days * 2  # 2 queries por día
    print(f"Días esperados: {expected_days}")
    print(f"Llamadas esperadas: {expected_calls}")

    return pendientes

if __name__ == "__main__":
    test_pendientes_logic()