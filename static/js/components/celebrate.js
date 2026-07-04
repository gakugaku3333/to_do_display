// 曜日タスク完了時の演出（紙吹雪 + 効果音）。ポイント制などのゲーミフィケーションは
// 運用が続かないため深追いせず、演出のみに留める。効果音はタブレット側でON/OFFできるよう
// localStorageに保存する（設定画面を作らない代わりに🔊ボタン1つで完結させる）。

const SOUND_PREF_KEY = 'celebrateSoundEnabled';
const CONFETTI_COLORS = ['#f5a623', '#ec4899', '#3b82f6', '#27ae60', '#9b59b6'];

function isSoundEnabled() {
  return localStorage.getItem(SOUND_PREF_KEY) !== 'off';
}

function setSoundEnabled(enabled) {
  localStorage.setItem(SOUND_PREF_KEY, enabled ? 'on' : 'off');
}

function spawnConfetti(el) {
  const rect = el.getBoundingClientRect();
  const originX = rect.left + rect.width / 2;
  const originY = rect.top + rect.height / 2;

  for (let i = 0; i < 16; i++) {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';
    piece.style.left = `${originX}px`;
    piece.style.top = `${originY}px`;
    piece.style.background = CONFETTI_COLORS[i % CONFETTI_COLORS.length];
    const angle = (Math.PI * 2 * i) / 16 + Math.random() * 0.5;
    const distance = 60 + Math.random() * 60;
    piece.style.setProperty('--dx', `${Math.cos(angle) * distance}px`);
    piece.style.setProperty('--dy', `${Math.sin(angle) * distance - 40}px`);
    document.body.appendChild(piece);
    piece.addEventListener('animationend', () => piece.remove());
  }
}

// Web Audio APIで短い「ター・ダ」を鳴らす（音声ファイルを同梱せずに済ませる）。
function playChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const notes = [523.25, 659.25, 783.99]; // C5, E5, G5
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      osc.type = 'sine';
      const start = ctx.currentTime + i * 0.1;
      gain.gain.setValueAtTime(0.15, start);
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.3);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.3);
    });
  } catch (_) { /* 非対応環境では無視 */ }
}

export function celebrate(el) {
  spawnConfetti(el);
  if (isSoundEnabled()) playChime();
}

export function initSoundToggle() {
  const btn = document.getElementById('sound-toggle-btn');
  if (!btn) return;

  const refresh = () => {
    btn.textContent = isSoundEnabled() ? '🔊' : '🔇';
  };
  refresh();

  btn.addEventListener('click', () => {
    setSoundEnabled(!isSoundEnabled());
    refresh();
  });
}
