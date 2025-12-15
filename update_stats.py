import os

path = r'c:\Repositorios\daily-questions-app\daily_questions_app\templates\stats.html'
modal_html = """
<!-- Modal para detalle del día -->
<div class="modal fade" id="modalDetalleDia" tabindex="-1" aria-labelledby="modalDetalleDiaLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="modalDetalleDiaLabel">
                    <i class="bi bi-calendar-day me-2"></i>
                    Objetivos del Día
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <!-- Resumen del día -->
                <div class="row g-3 mb-4">
                    <div class="col-md-4">
                        <div class="card border-0 bg-light">
                            <div class="card-body text-center py-2">
                                <div class="h5 mb-0 fw-bold text-primary" id="dia-total-objetivos">0</div>
                                <small class="text-muted">Total Objetivos</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card border-0 bg-light">
                            <div class="card-body text-center py-2">
                                <div class="h5 mb-0 fw-bold text-success" id="dia-completados">0</div>
                                <small class="text-muted">Completados</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card border-0 bg-light">
                            <div class="card-body text-center py-2">
                                <div class="h5 mb-0 fw-bold text-danger" id="dia-pendientes">0</div>
                                <small class="text-muted">Pendientes</small>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Filtros rápidos -->
                <div class="btn-group w-100 mb-3" role="group" id="filtros-dia">
                    <input type="radio" class="btn-check" name="filtro-dia" id="filtro-dia-todos" value="todos" checked>
                    <label class="btn btn-outline-secondary btn-sm" for="filtro-dia-todos">Todos</label>
                    
                    <input type="radio" class="btn-check" name="filtro-dia" id="filtro-dia-completados" value="completados">
                    <label class="btn btn-outline-success btn-sm" for="filtro-dia-completados">Completados</label>
                    
                    <input type="radio" class="btn-check" name="filtro-dia" id="filtro-dia-pendientes" value="pendientes">
                    <label class="btn btn-outline-danger btn-sm" for="filtro-dia-pendientes">Pendientes</label>
                </div>

                <!-- Lista de objetivos del día -->
                <div id="lista-objetivos-dia">
                    <!-- Se cargará dinámicamente -->
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    <i class="bi bi-x-circle me-1"></i>Cerrar
                </button>
            </div>
        </div>
    </div>
</div>
"""

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if '{% block scripts %}' in content:
    parts = content.split('{% block scripts %}')
    new_content = parts[0] + modal_html + '\n{% block scripts %}' + parts[1]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully inserted modal before scripts block")
else:
    parts = content.rsplit('{% endblock %}', 1)
    if len(parts) == 2:
        new_content = parts[0] + modal_html + '\n{% endblock %}' + parts[1]
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully inserted modal before last endblock")
    else:
        print("Could not find insertion point")
