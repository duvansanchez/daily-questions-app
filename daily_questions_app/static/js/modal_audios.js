// Mini-modal de audios
(function() {
  let filtrosRepasoActual = null;
  
  window.iniciarRepasoConAudios = async function() {
    const cat = document.getElementById('filtro-categoria-frases');
    const sub = document.getElementById('filtro-subcategoria-frases');
    filtrosRepasoActual = {categoria: cat?.value, subcategoria: sub?.value};
    
    try {
      const params = new URLSearchParams();
      if (filtrosRepasoActual.categoria) params.append('categoria', filtrosRepasoActual.categoria);
      if (filtrosRepasoActual.subcategoria) params.append('subcategoria', filtrosRepasoActual.subcategoria);
      
      const r = await fetch(`/api/audios?${params}`);
      if (!r.ok) {
        repasarTodasLasFrases();
        return;
      }
      
      const audios = await r.json();
      if (Array.isArray(audios) && audios.length > 0) {
        window.audiosParaRepasar = audios;
        const m = new bootstrap.Modal(document.getElementById('modalRepasarAudios'));
        document.getElementById('btn-repasar-audios').style.display = 'inline-block';
        document.getElementById('btn-saltar-audios').style.display = 'inline-block';
        document.getElementById('btn-continuar-frases').style.display = 'none';
        document.getElementById('lista-audios-repaso').style.display = 'none';
        document.querySelector('#modalRepasarAudios .modal-body p').style.display = 'block';
        m.show();
      } else {
        repasarTodasLasFrases();
      }
    } catch(e) {
      console.error('Error:', e);
      repasarTodasLasFrases();
    }
  };
  
  document.addEventListener('DOMContentLoaded', function() {
    const b1 = document.getElementById('btn-repasar-audios');
    if (b1) b1.addEventListener('click', function() {
      const audios = window.audiosParaRepasar || [];
      document.querySelector('#modalRepasarAudios .modal-body p').style.display = 'none';
      this.style.display = 'none';
      document.getElementById('btn-saltar-audios').style.display = 'none';
      
      const lista = document.getElementById('lista-audios-repaso');
      lista.style.display = 'block';
      lista.innerHTML = '<h6><i class="bi bi-music-note-beamed me-2"></i>Audios:</h6>';
      
      audios.forEach(a => {
        const div = document.createElement('div');
        div.className = 'mb-3 p-3 border rounded bg-light';
        let dur = '';
        if (a.duracion_segundos) {
          const m = Math.floor(a.duracion_segundos / 60);
          const s = a.duracion_segundos % 60;
          dur = `${m}:${s.toString().padStart(2,'0')}`;
        }
        div.innerHTML = `<div class="d-flex justify-content-between mb-2"><strong>${a.titulo}</strong>${dur?`<span class="badge bg-secondary">${dur}</span>`:''}</div>${a.descripcion?`<p class="text-muted small mb-2">${a.descripcion}</p>`:''}<audio controls class="w-100" style="height:40px;"><source src="${a.archivo_url}" type="audio/mpeg"></audio>`;
        lista.appendChild(div);
      });
      
      document.getElementById('btn-continuar-frases').style.display = 'inline-block';
    });
    
    const b2 = document.getElementById('btn-saltar-audios');
    if (b2) b2.addEventListener('click', function() {
      const m = bootstrap.Modal.getInstance(document.getElementById('modalRepasarAudios'));
      if (m) m.hide();
      repasarTodasLasFrases();
    });
    
    const b3 = document.getElementById('btn-continuar-frases');
    if (b3) b3.addEventListener('click', function() {
      const m = bootstrap.Modal.getInstance(document.getElementById('modalRepasarAudios'));
      if (m) m.hide();
      repasarTodasLasFrases();
    });
  });
})();
