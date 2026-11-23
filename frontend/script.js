/**
 * Pokémon Card Scanner - Frontend
 *
 * Fluxo:
 *  1. Foto: câmera ao vivo (HTTPS) ou câmera/galeria nativa do celular (funciona em HTTP)
 *  2. A foto é reduzida no próprio celular e enviada para /api/identify
 *  3. O backend lê a carta (Claude) e casa com o catálogo TCGdex -> candidatos
 *  4. Mostra a carta mais provável + alternativas, e o preço em R$ (/api/prices/<id>)
 */

const API = window.location.origin;

const CONDITION_MULT = { NM: 1, SP: 0.85, MP: 0.7, HP: 0.5, D: 0.3 };
const MAX_SIDE = 1600; // px – suficiente para ler o rodapé e leve para enviar

const state = {
  stream: null,
  facingMode: 'environment',
  photoBlob: null,
  photoUrl: null,
  detected: null,
  candidates: [],
  card: null,        // resumo da carta escolhida (id, name, number, set_name, image...)
  detail: null,      // detalhe da TCGdex (raridade, variantes)
  prices: null,
  variant: 'normal',
  condition: 'NM',
  configured: true,
};

const $ = (id) => document.getElementById(id);
const screens = ['home', 'scan', 'preview', 'search', 'result', 'collection'];

// ========================================
// Utilitários
// ========================================
function esc(text) {
  return String(text ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
function money(v) {
  return v == null || isNaN(v) ? '-' : brl.format(v);
}

function showScreen(name) {
  screens.forEach((s) => $(`screen-${s}`).classList.toggle('active', s === name));
  window.scrollTo(0, 0);
  if (name !== 'scan') stopCamera();
}

let toastTimer;
function toast(msg, duration = 3500) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), duration);
}

async function api(path, options) {
  const res = await fetch(`${API}${path}`, options);
  let data = {};
  try { data = await res.json(); } catch (_) { /* resposta sem JSON */ }
  if (!res.ok) throw new Error(data.error || `Erro ${res.status}`);
  return data;
}

function cardThumb(src, alt) {
  return src
    ? `<img src="${esc(src.replace('/high.', '/low.'))}" alt="${esc(alt)}" loading="lazy" />`
    : '<div class="thumb-placeholder">Sem imagem</div>';
}

// ========================================
// Foto: redimensionar antes de enviar
// ========================================
async function resizeImage(blob) {
  let bitmap;
  try {
    bitmap = await createImageBitmap(blob, { imageOrientation: 'from-image' });
  } catch (_) {
    // Safari antigo: carrega via <img>
    bitmap = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = URL.createObjectURL(blob);
    });
  }
  const w = bitmap.width, h = bitmap.height;
  const scale = Math.min(1, MAX_SIDE / Math.max(w, h));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(w * scale);
  canvas.height = Math.round(h * scale);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.88));
}

async function setPhoto(blob) {
  try {
    state.photoBlob = await resizeImage(blob);
  } catch (e) {
    console.error(e);
    toast('Não consegui abrir esta imagem.');
    return;
  }
  if (state.photoUrl) URL.revokeObjectURL(state.photoUrl);
  state.photoUrl = URL.createObjectURL(state.photoBlob);
  $('preview-image').src = state.photoUrl;
  $('detected-box').classList.add('hidden');
  showScreen('preview');
  if (state.configured) identifyPhoto(); // já começa a identificar
}

// ========================================
// Câmera ao vivo (só em HTTPS/localhost)
// ========================================
function canUseLiveCamera() {
  return window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
}

async function startCamera() {
  stopCamera();
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: state.facingMode, width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    const video = $('camera-video');
    video.srcObject = state.stream;
    await video.play();
  } catch (e) {
    console.error('Câmera:', e);
    showScreen('home');
    toast('Câmera ao vivo indisponível. Abrindo a câmera do celular...');
    $('input-camera').click();
  }
}

function stopCamera() {
  if (state.stream) {
    state.stream.getTracks().forEach((t) => t.stop());
    state.stream = null;
    $('camera-video').srcObject = null;
  }
}

function openScanner() {
  if (canUseLiveCamera()) {
    showScreen('scan');
    startCamera();
  } else {
    // Sem HTTPS: usa a câmera nativa (input capture), que funciona em qualquer navegador
    $('input-camera').click();
  }
}

function capturePhoto() {
  const video = $('camera-video');
  if (!video.videoWidth) {
    toast('Câmera ainda não está pronta.');
    return;
  }
  const canvas = $('camera-canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  canvas.toBlob((blob) => { stopCamera(); setPhoto(blob); }, 'image/jpeg', 0.92);
}

// ========================================
// Identificação pela foto
// ========================================
async function identifyPhoto() {
  if (!state.photoBlob) return;
  const status = $('analyze-status');
  const box = $('detected-box');
  status.classList.remove('hidden');
  $('analyze-status-text').textContent = 'Identificando a carta...';
  $('btn-analyze').disabled = true;
  box.classList.add('hidden');

  try {
    const form = new FormData();
    form.append('image', state.photoBlob, 'carta.jpg');
    const data = await api('/api/identify', { method: 'POST', body: form });

    state.detected = data.detected || null;
    state.candidates = data.candidates || [];

    if (!state.candidates.length) {
      renderDetected(data.message || 'Não encontrei esta carta no catálogo.');
      return;
    }
    const hint = state.detected?.variant_hint;
    state.variant = ['holo', 'reverse', 'first_edition', 'normal'].includes(hint) ? hint : null;
    await openCard(state.candidates[0], { confident: data.confident, fromPhoto: true });
  } catch (e) {
    console.error(e);
    renderDetected(e.message);
  } finally {
    status.classList.add('hidden');
    $('btn-analyze').disabled = false;
  }
}

function renderDetected(message) {
  const d = state.detected;
  const box = $('detected-box');
  const read = d && d.is_pokemon_card
    ? `<p><strong>Li na carta:</strong> ${esc(d.name || '?')} • Nº ${esc(d.number || '?')}${d.set_total ? '/' + esc(d.set_total) : ''}</p>`
    : '';
  box.innerHTML = `
    <p>${esc(message)}</p>
    ${read}
    ${d?.notes ? `<p class="muted">${esc(d.notes)}</p>` : ''}
    <button class="btn btn-primary btn-small" id="btn-detected-search">🔍 Buscar pelo nome</button>
  `;
  box.classList.remove('hidden');
  $('btn-detected-search').onclick = () => openSearch(d?.name_en || d?.name || '');
}

// ========================================
// Resultado
// ========================================
async function openCard(card, { confident = true, fromPhoto = false } = {}) {
  state.card = card;
  state.detail = null;
  state.prices = null;

  $('result-name').textContent = card.name || 'Carta';
  $('result-set').textContent = card.set_name || card.set_id || 'Coleção';
  $('result-number').textContent = 'Nº ' + (card.number || '-') + (card.set_total ? '/' + card.set_total : '');
  $('result-rarity').textContent = '…';
  const lang = state.detected?.language_label;
  $('result-language').textContent = lang || '';
  $('result-language').classList.toggle('hidden', !lang);
  setImage($('result-image'), card.image);

  const badge = $('result-badge');
  badge.textContent = fromPhoto ? (confident ? '✅ Identificada' : '⚠️ Confira a carta') : 'Selecionada';
  badge.classList.toggle('warn', fromPhoto && !confident);

  const photo = $('result-photo');
  if (fromPhoto && state.photoUrl) {
    photo.src = state.photoUrl;
    photo.classList.remove('hidden');
  } else if (!fromPhoto) {
    photo.classList.add('hidden');
  }

  renderAlternatives();
  showScreen('result');

  try {
    state.detail = await api(`/api/cards/${encodeURIComponent(card.id)}`);
    $('result-rarity').textContent = state.detail.rarity || '—';
    if (state.detail.set_name) $('result-set').textContent = state.detail.set_name;
    if (state.detail.set_total) {
      $('result-number').textContent = `Nº ${state.detail.number}/${state.detail.set_total}`;
    }
    if (!state.variant) state.variant = defaultVariant(state.detail.variants);
  } catch (e) {
    $('result-rarity').textContent = '—';
  }
  $('result-variant').value = state.variant || 'normal';
  loadPrices();
}

function defaultVariant(v) {
  if (!v) return 'normal';
  if (v.normal) return 'normal';
  if (v.holo) return 'holo';
  if (v.reverse) return 'reverse';
  if (v.firstEdition) return 'first_edition';
  return 'normal';
}

function setImage(img, src) {
  img.onerror = () => { img.onerror = null; img.removeAttribute('src'); img.alt = 'Imagem não disponível'; };
  if (src) img.src = src; else img.removeAttribute('src');
}

function renderAlternatives() {
  const others = state.candidates.filter((c) => c.id !== state.card?.id);
  const wrap = $('alternatives');
  const list = $('alternatives-list');
  if (!others.length) {
    wrap.classList.toggle('hidden', !state.candidates.length);
    list.innerHTML = '';
    return;
  }
  list.innerHTML = others.map((c, i) => `
    <button class="alt-card" data-i="${i}">
      ${cardThumb(c.image, c.name)}
      <span>${esc(c.name)}</span>
      <small>${esc(c.set_name || c.set_id || '')} • ${esc(c.number || '')}</small>
    </button>`).join('');
  list.querySelectorAll('.alt-card').forEach((btn) => {
    btn.onclick = () => openCard(others[Number(btn.dataset.i)], { confident: true, fromPhoto: true });
  });
  wrap.classList.remove('hidden');
}

// ========================================
// Preços
// ========================================
async function loadPrices() {
  const card = state.card;
  $('prices-loading').classList.remove('hidden');
  $('prices-content').classList.add('hidden');
  $('prices-error').classList.add('hidden');

  try {
    const data = await api(`/api/prices/${encodeURIComponent(card.id)}?variant=${encodeURIComponent(state.variant || 'unknown')}`);
    if (state.card !== card) return; // usuário trocou de carta no meio
    state.prices = data;

    if (data.links) {
      $('link-liga').href = data.links.liga;
      $('link-myp').href = data.links.mypcards;
    }

    if (!data.available) {
      $('prices-error-text').textContent = data.message || 'Sem preço de mercado para esta carta.';
      $('prices-error').classList.remove('hidden');
      renderSell();
      return;
    }

    $('price-ref').textContent = money(data.reference);
    $('price-ref-source').textContent = `${data.reference_source} • versão ${data.variant || '-'}`;
    const cm = data.cardmarket || {};
    $('price-cm-low').textContent = money(cm.low);
    $('price-cm-trend').textContent = money(cm.trend);
    $('price-cm-avg30').textContent = money(cm.avg30);
    const tpv = (data.tcgplayer?.variants || []).find((v) => v.label === data.variant) || data.tcgplayer?.variants?.[0];
    $('price-tp-market').textContent = money(tpv?.market);

    const r = data.rates || {};
    $('price-note').textContent =
      `Preços internacionais convertidos pela cotação do dia (US$ 1 = ${money(r.USD)}, € 1 = ${money(r.EUR)}). ` +
      'O preço no Brasil pode ser diferente: confira nos links abaixo.';
    $('prices-content').classList.remove('hidden');
  } catch (e) {
    $('prices-error-text').textContent = e.message;
    $('prices-error').classList.remove('hidden');
  } finally {
    $('prices-loading').classList.add('hidden');
    renderSell();
  }
}

function conditionPrice() {
  const ref = state.prices?.reference;
  return ref == null ? null : ref * (CONDITION_MULT[state.condition] ?? 1);
}

function renderSell() {
  const p = conditionPrice();
  $('sell-ref').textContent = money(p);
  $('sell-competitive').textContent = money(p == null ? null : p * 0.9);
  $('sell-fast').textContent = money(p == null ? null : p * 0.75);
}

// ========================================
// Busca por nome
// ========================================
function openSearch(prefill = '') {
  $('manual-card-name').value = prefill;
  $('manual-search-results').innerHTML = '';
  showScreen('search');
  if (prefill) searchByName();
  else $('manual-card-name').focus();
}

async function searchByName() {
  const q = $('manual-card-name').value.trim();
  if (!q) { toast('Digite o nome da carta.'); return; }
  const out = $('manual-search-results');
  out.innerHTML = '<p class="muted center">Buscando...</p>';
  try {
    const data = await api(`/api/cards/search?q=${encodeURIComponent(q)}`);
    if (!data.cards.length) {
      out.innerHTML = '<p class="muted center">Nenhuma carta encontrada.</p>';
      return;
    }
    out.innerHTML = data.cards.map((c, i) => `
      <div class="collection-item clickable" data-i="${i}">
        ${cardThumb(c.image, c.name)}
        <div class="collection-item-info">
          <div class="collection-item-name">${esc(c.name)}</div>
          <div class="collection-item-meta">${esc(c.set_name || c.set_id || 'Coleção')} • Nº ${esc(c.number || '-')}</div>
        </div>
      </div>`).join('') +
      (data.total > data.cards.length ? `<p class="muted center">Mostrando ${data.cards.length} de ${data.total}. Refine a busca.</p>` : '');
    out.querySelectorAll('.collection-item').forEach((el) => {
      el.onclick = () => {
        state.candidates = [];
        state.detected = null;
        state.variant = null;
        openCard(data.cards[Number(el.dataset.i)], { fromPhoto: false });
      };
    });
  } catch (e) {
    out.innerHTML = `<p class="center error">${esc(e.message)}</p>`;
  }
}

// ========================================
// Coleção
// ========================================
function renderCollectionList(container, cards, { removable = false } = {}) {
  container.innerHTML = cards.map((c) => `
    <div class="collection-item">
      ${cardThumb(c.image_url, c.name)}
      <div class="collection-item-info">
        <div class="collection-item-name">${esc(c.name)}</div>
        <div class="collection-item-meta">${esc(c.set_name || 'Coleção')} • Nº ${esc(c.number || '-')} • ${esc(c.condition || 'NM')}</div>
      </div>
      <div class="collection-item-price">${money(c.price_found)}</div>
      ${removable ? `<button class="icon-btn remove" data-id="${Number(c.id)}" title="Remover">🗑️</button>` : ''}
    </div>`).join('');
  container.querySelectorAll('.remove').forEach((btn) => {
    btn.onclick = async () => {
      if (!confirm('Remover esta carta da coleção?')) return;
      try {
        await api(`/api/collection/${btn.dataset.id}`, { method: 'DELETE' });
        loadCollection();
      } catch (e) { toast(e.message); }
    };
  });
}

async function loadHome() {
  try {
    const data = await api('/api/collection');
    $('stat-total').textContent = data.total_cards || 0;
    $('stat-value').textContent = money(data.total_value || 0);
    const recent = (data.cards || []).slice(0, 5);
    $('empty-recent').style.display = recent.length ? 'none' : 'block';
    renderCollectionList($('recent-list'), recent);
  } catch (e) {
    console.error(e);
  }
}

async function loadCollection() {
  try {
    const data = await api('/api/collection');
    const total = data.total_cards || 0;
    $('coll-total').textContent = total;
    $('coll-value').textContent = money(data.total_value || 0);
    $('coll-avg').textContent = total ? money(data.total_value / total) : '-';
    $('coll-empty').style.display = total ? 'none' : 'block';
    renderCollectionList($('coll-list'), data.cards || [], { removable: true });
  } catch (e) {
    toast('Erro ao carregar a coleção.');
  }
}

async function saveToCollection() {
  const c = state.card;
  if (!c) return;
  const price = conditionPrice();
  try {
    await api('/api/collection', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        card_id: c.id,
        name: c.name,
        set_name: state.detail?.set_name || c.set_name,
        number: c.number,
        rarity: state.detail?.rarity,
        language: state.detected?.language_label || null,
        image_url: c.image,
        condition: state.condition,
        price_found: price == null ? null : Math.round(price * 100) / 100,
        price_source: state.prices?.reference_source || null,
      }),
    });
    toast('Carta salva na coleção!');
    showScreen('home');
    loadHome();
  } catch (e) {
    toast('Erro ao salvar: ' + e.message);
  }
}

// ========================================
// Eventos
// ========================================
function bindFileInput(input) {
  input.addEventListener('change', (e) => {
    const file = e.target.files[0];
    e.target.value = ''; // permite escolher a mesma foto de novo
    if (file) setPhoto(file);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  bindFileInput($('input-camera'));
  bindFileInput($('input-gallery'));

  $('btn-scan').onclick = openScanner;
  $('btn-upload').onclick = () => $('input-gallery').click();
  $('btn-search-name').onclick = () => openSearch();
  $('btn-collection').onclick = () => { showScreen('collection'); loadCollection(); };

  $('btn-capture').onclick = capturePhoto;
  $('btn-scan-back').onclick = () => showScreen('home');
  $('btn-switch-camera').onclick = () => {
    state.facingMode = state.facingMode === 'environment' ? 'user' : 'environment';
    startCamera();
  };

  $('btn-retake').onclick = openScanner;
  $('btn-analyze').onclick = () => {
    if (!state.configured) { openSearch(); return; }
    identifyPhoto();
  };

  $('btn-search-back').onclick = () => showScreen(state.photoBlob ? 'preview' : 'home');
  $('btn-search-manual').onclick = searchByName;
  $('manual-card-name').addEventListener('keydown', (e) => { if (e.key === 'Enter') searchByName(); });

  $('btn-back-home').onclick = () => { showScreen('home'); loadHome(); };
  $('btn-new-scan').onclick = openScanner;
  $('btn-save-collection').onclick = saveToCollection;
  $('btn-alt-search').onclick = () => openSearch(state.detected?.name_en || state.card?.name || '');
  $('result-variant').onchange = (e) => { state.variant = e.target.value; loadPrices(); };

  document.querySelectorAll('.condition-chip').forEach((chip) => {
    chip.classList.toggle('active', chip.dataset.condition === state.condition);
    chip.onclick = () => {
      document.querySelectorAll('.condition-chip').forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      state.condition = chip.dataset.condition;
      renderSell();
    };
  });

  $('btn-collection-back').onclick = () => { showScreen('home'); loadHome(); };
  let searchTimer;
  $('coll-search').addEventListener('input', (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(async () => {
      try {
        const data = await api(`/api/collection/search?q=${encodeURIComponent(e.target.value)}`);
        renderCollectionList($('coll-list'), data.cards || [], { removable: true });
      } catch (_) { /* ignora */ }
    }, 250);
  });

  api('/health').then((h) => {
    state.configured = !!h.photo_identification;
    $('config-warning').classList.toggle('hidden', state.configured);
  }).catch(() => {});

  loadHome();
});
