import { getApiToken } from './api.js';
import { getState, setState, subscribe } from './state.js';
import { showStatusBanner, hideStatusBanner } from './components/statusBanner.js';
import { initHealthBanner } from './components/healthBanner.js';
import { initClock } from './components/clock.js';
import * as dateHeader from './components/dateHeader.js';
import * as weather from './components/weather.js';
import * as events from './components/events.js';
import * as tasks from './components/tasks.js';
import * as proposals from './components/proposals.js';
import { initWeeklyTasks } from './components/weeklyTasks.js';
import { initWeekModal } from './components/weekModal.js';

// 各コンポーネントは自分の担当コンテナだけを再描画する（規約1）。
// 状態が変わるたびに全コンポーネントへ通知し、各自が必要な部分だけ更新する。
const renderers = [dateHeader.render, weather.render, events.render, tasks.render, proposals.render];

subscribe((state) => {
  for (const render of renderers) render(state);
});

initClock();
initHealthBanner();
tasks.initTasks();
proposals.initProposals();
initWeeklyTasks();
initWeekModal();

// ===== SSE接続 =====
let eventSource = null;

function connectSSE() {
  if (eventSource) eventSource.close();

  const token = getApiToken();
  const url = token ? `/api/stream?token=${encodeURIComponent(token)}` : '/api/stream';
  eventSource = new EventSource(url);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      setState({ data, proposals: data.proposals || [] });
      hideStatusBanner();
    } catch (err) {
      console.error('SSEデータのパースエラー:', err);
    }
  };

  eventSource.onerror = () => {
    showStatusBanner('接続が切れました。再接続中...', 'warning');
    // EventSource は自動再接続する
  };

  eventSource.onopen = () => {
    hideStatusBanner();
  };
}

// ===== Screen Wake Lock (タブレットのスリープ防止) =====
// 画面をOFFにすべき時間帯は Wake Lock を解放する（Mac側のADBスケジュールで画面を
// スリープさせるため、ここで起こし続けると喧嘩する）。スケジュールはMac側と一致:
//   共通          : 21:30–06:00 はOFF
//   平日(月–金・非祝日): さらに 08:00–15:00 もOFF
//   土日・祝日     : 夜間のみOFF
// 祝日判定は SSE データの is_holiday を使う。
function shouldScreenBeOff() {
  const n = new Date();
  const hm = n.getHours() * 100 + n.getMinutes(); // 例 21:30 → 2130
  if (hm >= 2130 || hm < 600) return true;        // 夜間（共通）
  const dow = n.getDay();                          // 0=日..6=土
  const isWeekday = dow >= 1 && dow <= 5;
  const isHoliday = !!(getState().data && getState().data.is_holiday);
  if (isWeekday && !isHoliday && hm >= 800 && hm < 1500) return true; // 平日の日中
  return false;
}

let wakeLockSentinel = null;

async function acquireWakeLock() {
  if (wakeLockSentinel) return;
  try {
    wakeLockSentinel = await navigator.wakeLock.request('screen');
    wakeLockSentinel.addEventListener('release', () => { wakeLockSentinel = null; });
  } catch (_) { /* 非対応ブラウザでは無視 */ }
}

async function releaseWakeLock() {
  try { if (wakeLockSentinel) await wakeLockSentinel.release(); } catch (_) { /* noop */ }
  wakeLockSentinel = null;
}

function manageWakeLock() {
  if (document.visibilityState !== 'visible' || shouldScreenBeOff()) {
    releaseWakeLock();
  } else {
    acquireWakeLock();
  }
}

document.addEventListener('visibilitychange', () => {
  manageWakeLock();
  if (document.visibilityState === 'visible') {
    if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
      connectSSE();
    }
  }
});

setInterval(manageWakeLock, 60 * 1000); // 夜間境界をまたいだ切り替え用（毎分判定）
manageWakeLock();

// ===== 定期リロード（保険・1日1回 深夜帯）=====
// データはSSEで常時更新されるため、中身の最新化目的のリロードは不要。
// JSのメモリリーク・描画フリーズ・デプロイ後のSW更新ズレからの自動復帰が目的。
// 誰も見ていない早朝(4:00台)に1日1回だけ全リロードする。
const RELOAD_HOUR = 4;
setInterval(() => {
  const now = new Date();
  if (now.getHours() !== RELOAD_HOUR) return;
  const today = now.toISOString().slice(0, 10);
  if (localStorage.getItem('lastDailyReload') === today) return;
  localStorage.setItem('lastDailyReload', today);
  window.location.reload();
}, 60 * 1000);

// ===== 初期化 =====
connectSSE();
