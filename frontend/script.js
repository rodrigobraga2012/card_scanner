/**
 * Pokémon Card Scanner - Frontend (JavaScript)
 * Baseado na conversa com o ChatGPT sobre o scanner de cartas Pokémon.
 *
 * Funcionalidades:
 * - Acesso à câmera do celular (WebRTC / MediaDevices)
 * - Captura de foto
 * - Pré-visualização antes de analisar
 * - Consulta ao backend Flask para identificação (TCGdex) e preços (MYP Cards)
 * - Salvar na coleção local (via API do backend)
 * - PWA (instalável)
 */

const API_BASE = window.location.origin; // mesmo endereço do servidor Flask

// Estado da aplicação
let state = {
  currentScreen: 'home',
  stream: null,
  capturedImage: null,     // base64 da foto capturada
  currentCard: null,       // dados da carta identificada
  currentCondition: 'NM',
};

// Elementos DOM
const screens = {
  home: document.getElementById('screen-home'),
  scan: document.getElementById('screen-scan'),
  preview: document.getElementById('screen-preview'),
  result: document.getElementById('screen-result'),
  collection: document.getElementById('screen-collection'),
};

const video = document.getElementById('camera-video');
const canvas = document.getElementById('camera-canvas');
const previewImage = document.getElementById('preview-image');

// ========================================
// Navegação entre telas
// ========================================
function showScreen(name) {
  Object.values(screens).forEach(s => s.classList.remove('active'));
  screens[name].classList.add('active');
  state.currentScreen = name;
  window.scrollTo(0, 0);
}

function toast(msg, duration = 3000) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), duration);
}

// ========================================
// Tela inicial
// ========================================
async function loadHome() {
  try {
    const res = await fetch(`${API_BASE}/api/collection`);
    const data = await res.json();

    document.getElementById('stat-total').textContent = data.total_cards || 0;
    document.getElementById('stat-value').textContent =
      'R$ ' + (data.total_value || 0).toFixed(2).replace('.', ',');

    // Últimas cartas
    const recentList = document.getElementById('recent-list');
    const emptyMsg = document.getElementById('empty-recent');
    recentList.innerHTML = '';

    const recent = (data.cards || []).slice(0, 5);
    if (recent.length === 0) {
      emptyMsg.style.display = 'block';
    } else {
      emptyMsg.style.display = 'none';
      recent.forEach(c => {
        const el = document.createElement('div');
        el.className = 'collection-item';
        el.innerHTML = `
          ${c.image_url ? `<img src="${c.image_url}" alt="${c.name}" />` : `<div style="width:64px;height:88px;background:#f0f0f0;border-radius:8px;"></div>`}
          <div class="collection-item-info">
            <div class="collection-item-name">${escapeHtml(c.name)}</div>
            <div class="collection-item-meta">
              ${c.set_name || 'Coleção'} • #${c.number || '-'} • ${c.condition || 'NM'}
            </div>
          </div>
          <div class="collection-item-price">
            ${c.price_found != null ? 'R$ ' + c.price_found.toFixed(2).replace('.', ',') : '-'}
          </div>
        `;
        recentList.appendChild(el);
      });
    }
  } catch (e) {
    console.error('Erro ao carregar home:', e);
    toast('Erro ao carregar dados iniciais');
  }
}

// ========================================
// Câmera
// ========================================
async function startCamera() {
  try {
    const constraints = {
      video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
    };
    state.stream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = state.stream;
    await video.play();
    toast('Câmera ativada. Posicione a carta.');
  } catch (e) {
    console.error('Erro ao acessar câmera:', e);
    toast('Não foi possível acessar a câmera. Use "Enviar foto".');
  }
}

function stopCamera() {
  if (state.stream) {
    state.stream.getTracks().forEach(track => track.stop());
    state.stream = null;
    video.srcObject = null;
  }
}

function switchCamera() {
  // Simples: recarrega a câmera (em produção, alternar facingMode)
  stopCamera();
  startCamera();
}

// Capturar foto
function capturePhoto() {
  if (!video.videoWidth) {
    toast('Câmera ainda não pronta.');
    return;
  }

  const ctx = canvas.getContext('2d');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  ctx.drawImage(video, 0, 0);

  const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
  state.capturedImage = dataUrl;

  stopCamera();
  previewImage.src = dataUrl;
  showScreen('preview');
}

// ========================================
// Análise da carta (envia para backend)
// ========================================
async function analyzeCard() {
  if (!state.capturedImage) {
    toast('Nenhuma imagem capturada.');
    return;
  }

  // Mostrar status de carregamento
  const status = document.getElementById('scan-status');
  const statusText = document.getElementById('scan-status-text');
  status.classList.remove('hidden');
  statusText.textContent = 'Identificando carta...';

  try {
    // Envia imagem para o backend (endpoint de busca por imagem não existe no MVP,
    // então simulamos: o usuário teria que informar o nome ou usamos OCR no futuro).
    // Para este MVP, vamos pedir ao backend uma busca genérica ou usar dados simulados.
    // Aqui, faremos uma busca por "Pikachu" como exemplo ou podemos extrair texto via OCR.
    // Por enquanto, vamos permitir que o usuário edite/confira o nome.

    // Simulação: vamos buscar uma carta popular no TCGdex apenas para demonstrar o fluxo
    // Em produção, isso viria do OCR + comparação de imagem.
    const searchRes = await fetch(`${API_BASE}/api/cards/search?q=Pikachu`);
    const searchData = await searchRes.json();

    if (searchData.cards && searchData.cards.length > 0) {
      const card = searchData.cards[0];
      state.currentCard = {
        name: card.localized_name || card.name,
        set_name: card.set_name || 'Desconhecida',
        number: card.number || '-',
        rarity: card.rarity || 'Comum',
        language: card.language || 'Inglês',
        image: card.image,
        variant: 'Normal',
      };
      showResult();
    } else {
      throw new Error('Nenhuma carta encontrada');
    }
  } catch (e) {
    console.error('Erro ao analisar:', e);
    toast('Não foi identificar a carta automaticamente.');
  } finally {
    status.classList.add('hidden');
  }
}

function showResult() {
  if (!state.currentCard) return;

  const c = state.currentCard;
  document.getElementById('result-image').src = c.image || 'https://via.placeholder.com/300x400?text=Carta';
  document.getElementById('result-name').textContent = c.name;
  document.getElementById('result-set').textContent = c.set_name;
  document.getElementById('result-number').textContent = 'Nº ' + c.number;
  document.getElementById('result-rarity').textContent = c.rarity;
  document.getElementById('result-language').textContent = c.language;
  document.getElementById('result-variant').textContent = 'Versão: ' + c.variant;

  // Preços - consultar MYP Cards
  loadPrices(c);

  showScreen('result');
}

async function loadPrices(card) {
  const loading = document.getElementById('prices-loading');
  const content = document.getElementById('prices-content');
  const error = document.getElementById('prices-error');

  loading.classList.remove('hidden');
  content.classList.add('hidden');
  error.classList.add('hidden');

  try {
    const res = await fetch(`${API_BASE}/api/prices/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: card.name,
        set: card.set_name,
        number: card.number,
        rarity: card.rarity,
        language: card.language,
      }),
    });
    const data = await res.json();

    loading.classList.add('hidden');

    if (!data.configured) {
      // MYP Cards não configurado
      error.classList.remove('hidden');
      document.getElementById('btn-mypcards-link').onclick = () => {
        window.open('https://mypcards.com/pokemon', '_blank');
      };
      return;
    }

    if (data.prices) {
      content.classList.remove('hidden');
      // Preencher com dados reais quando o endpoint estiver implementado
      document.getElementById('price-min').textContent = data.prices.min || '-';
      document.getElementById('price-avg').textContent = data.prices.avg || '-';
      document.getElementById('price-max').textContent = data.prices.max || '-';
      document.getElementById('price-count').textContent = data.prices.count || '-';
      document.getElementById('price-note').textContent = data.prices.note || '';
    } else {
      content.classList.remove('hidden');
      document.getElementById('price-note').textContent =
        data.message || 'Preços indisponíveis no momento.';
    }
  } catch (e) {
    console.error('Erro ao carregar preços:', e);
    loading.classList.add('hidden');
    error.classList.remove('hidden');
  }
}

// ========================================
// Salvar na coleção
// ========================================
async function saveToCollection() {
  if (!state.currentCard) return;

  const c = state.currentCard;
  try {
    const res = await fetch(`${API_BASE}/api/collection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: c.name,
        set_name: c.set_name,
        number: c.number,
        rarity: c.rarity,
        language: c.language,
        image_url: c.image,
        condition: state.currentCondition,
        price_found: null, // preço será consultado depois
        price_source: 'TCGdex / MYP Cards',
      }),
    });

    if (res.ok) {
      toast('Carta salva na coleção!');
      showScreen('home');
      loadHome();
    } else {
      toast('Erro ao salvar carta.');
    }
  } catch (e) {
    console.error('Erro ao salvar:', e);
    toast('Erro ao salvar na coleção.');
  }
}

// ========================================
// Tela da coleção
// ========================================
async function loadCollection() {
  try {
    const res = await fetch(`${API_BASE}/api/collection`);
    const data = await res.json();

    document.getElementById('coll-total').textContent = data.total_cards || 0;
    document.getElementById('coll-value').textContent =
      'R$ ' + (data.total_value || 0).toFixed(2).replace('.', ',');
    document.getElementById('coll-avg').textContent = data.total_cards
      ? 'R$ ' + ((data.total_value / data.total_cards).toFixed(2)).replace('.', ',')
      : '-';

    const list = document.getElementById('coll-list');
    const empty = document.getElementById('coll-empty');
    list.innerHTML = '';

    const cards = data.cards || [];
    if (cards.length === 0) {
      empty.style.display = 'block';
    } else {
      empty.style.display = 'none';
      cards.forEach(card => {
        const el = document.createElement('div');
        el.className = 'collection-item';
        el.innerHTML = `
          ${card.image_url ? `<img src="${card.image_url}" alt="${card.name}" />` : `<div style="width:64px;height:88px;background:#f0f0f0;border-radius:8px;"></div>`}
          <div class="collection-item-info">
            <div class="collection-item-name">${escapeHtml(card.name)}</div>
            <div class="collection-item-meta">
              ${card.set_name || 'Coleção'} • #${card.number || '-'} • ${card.condition || 'NM'}
            </div>
          </div>
          <div class="collection-item-price">
            ${card.price_found != null ? 'R$ ' + card.price_found.toFixed(2).replace('.', ',') : '-'}
          </div>
        `;
        list.appendChild(el);
      });
    }
  } catch (e) {
    console.error('Erro ao carregar coleção:', e);
    toast('Erro ao carregar coleção.');
  }
}

// ========================================
// Condição da carta
// ========================================
function setupConditionChips() {
  const chips = document.querySelectorAll('.condition-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      state.currentCondition = chip.dataset.condition;
    });
  });
  // Selecionar NM por padrão
  const nm = document.querySelector('.condition-chip[data-condition="NM"]');
  if (nm) nm.classList.add('active');
}

// ========================================
// Utilitários
// ========================================
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ========================================
// Event Listeners
// ========================================
document.addEventListener('DOMContentLoaded', () => {
  // Tela inicial
  document.getElementById('btn-scan').addEventListener('click', () => {
    showScreen('scan');
    startCamera();
  });

  document.getElementById('btn-upload').addEventListener('click', () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (evt) => {
        state.capturedImage = evt.target.result;
        previewImage.src = state.capturedImage;
        showScreen('preview');
      };
      reader.readAsDataURL(file);
    };
    input.click();
  });

  document.getElementById('btn-collection').addEventListener('click', () => {
    showScreen('collection');
    loadCollection();
  });

  // Tela de escaneamento
  document.getElementById('btn-capture').addEventListener('click', capturePhoto);
  document.getElementById('btn-switch-camera').addEventListener('click', switchCamera);

  // Tela de prévia
  document.getElementById('btn-retake').addEventListener('click', () => {
    showScreen('scan');
    startCamera();
  });

  document.getElementById('btn-analyze').addEventListener('click', analyzeCard);

  // Tela de resultado
  document.getElementById('btn-back-home').addEventListener('click', () => {
    showScreen('home');
    loadHome();
  });

  document.getElementById('btn-new-scan').addEventListener('click', () => {
    state.capturedImage = null;
    state.currentCard = null;
    showScreen('scan');
    startCamera();
  });

  document.getElementById('btn-save-collection').addEventListener('click', saveToCollection);

  // Tela da coleção
  document.getElementById('btn-collection-back').addEventListener('click', () => {
    showScreen('home');
    loadHome();
  });

  document.getElementById('coll-search').addEventListener('input', (e) => {
    const q = e.target.value;
    fetch(`${API_BASE}/api/collection/search?q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(data => {
        const list = document.getElementById('coll-list');
        list.innerHTML = '';
        (data.cards || []).forEach(card => {
          const el = document.createElement('div');
          el.className = 'collection-item';
          el.innerHTML = `
            ${card.image_url ? `<img src="${card.image_url}" alt="${card.name}" />` : `<div style="width:64px;height:88px;background:#f0f0f0;border-radius:8px;"></div>`}
            <div class="collection-item-info">
              <div class="collection-item-name">${escapeHtml(card.name)}</div>
              <div class="collection-item-meta">
                ${card.set_name || 'Coleção'} • #${card.number || '-'} • ${card.condition || 'NM'}
              </div>
            </div>
            <div class="collection-item-price">
              ${card.price_found != null ? 'R$ ' + card.price_found.toFixed(2).replace('.', ',') : '-'}
            </div>
          `;
          list.appendChild(el);
        });
      });
  });

  // Condição
  setupConditionChips();

  // Inicial
  loadHome();
});
