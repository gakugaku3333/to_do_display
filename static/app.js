'use strict';

// ===== 認証トークン =====
const API_TOKEN = document.querySelector('meta[name="api-token"]')?.content || '';

function authHeaders(includeContentType = false) {
  const h = {};
  if (includeContentType) h['Content-Type'] = 'application/json';
  if (API_TOKEN) h['Authorization'] = `Bearer ${API_TOKEN}`;
  return h;
}

// ===== 時計 =====
function updateClock() {
  const now = new Date();
  const h = String(now.getHours()).padStart(2, '0');
  const m = String(now.getMinutes()).padStart(2, '0');
  document.getElementById('clock').textContent = `${h}:${m}`;
}

setInterval(updateClock, 1000);
updateClock();

// ===== ステータスバナー =====
function showStatusBanner(message, type) {
  const el = document.getElementById('status-banner');
  el.textContent = message;
  el.className = `status-banner ${type}`;
}

function hideStatusBanner() {
  const el = document.getElementById('status-banner');
  el.className = 'hidden';
}

// ===== 日付表示 =====
function updateDateDisplay(data) {
  const dateEl = document.getElementById('date-info');
  const d = new Date(data.date + 'T00:00:00');
  const year = d.getFullYear();
  const month = d.getMonth() + 1;
  const day = d.getDate();
  const jsDay = d.getDay(); // 0=日, 6=土
  const refreshText = data.last_refresh ? `更新 ${data.last_refresh}` : '';

  // 色分け: 祝日・日曜→赤、土曜→青
  let dayClass = '';
  if (data.is_holiday || jsDay === 0) dayClass = 'holiday';
  else if (jsDay === 6) dayClass = 'saturday';

  const holidayBadge = data.holiday_name
    ? `<span class="holiday-badge">${data.holiday_name}</span>`
    : '';

  dateEl.innerHTML = `<span class="date-main ${dayClass}">${year}年${month}月${day}日（${data.weekday.replace('曜日', '')}）${holidayBadge}</span>`;

  const refreshEl = document.getElementById('last-refresh');
  if (refreshEl) refreshEl.textContent = refreshText;
}

// ===== イベント描画 =====
function renderEvents(events) {
  const list = document.getElementById('events-list');
  list.innerHTML = '';

  if (events.length === 0) {
    list.innerHTML = '<div class="empty-state">今日の予定はありません</div>';
    return;
  }

  for (const ev of events) {
    const el = document.createElement('div');
    el.className = 'event-item';

    const dot = document.createElement('div');
    dot.className = 'event-dot';
    dot.style.background = ev.color;

    const timeEl = document.createElement('div');
    timeEl.className = 'event-time';
    if (ev.is_all_day) {
      timeEl.textContent = '';
    } else {
      timeEl.textContent = ev.start_time;
    }

    const titleEl = document.createElement('div');
    titleEl.className = 'event-title';
    titleEl.textContent = ev.title;

    el.appendChild(dot);
    el.appendChild(timeEl);
    el.appendChild(titleEl);

    if (ev.is_all_day) {
      const badge = document.createElement('div');
      badge.className = 'event-allday';
      badge.textContent = '終日';
      el.appendChild(badge);
    }

    list.appendChild(el);
  }
}

// ===== タスク描画 =====
function formatDueDate(dueDateStr, isOverdue) {
  if (!dueDateStr) return '';
  const d = new Date(dueDateStr + 'T00:00:00');
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const label = isOverdue ? `⚠ 期限切れ: ${m}/${day}` : `期限: ${m}/${day}`;
  return label;
}

function createTaskElement(task) {
  const el = document.createElement('div');
  el.className = 'task-item';
  el.dataset.taskId = task.id;
  el.dataset.taskType = task.task_type;
  el.dataset.dueDate = task.due_date || '';

  if (task.is_overdue) el.classList.add('overdue');
  if (task.is_completed) el.classList.add('completed');

  const checkbox = document.createElement('div');
  checkbox.className = 'task-checkbox';
  const checkIcon = document.createElement('span');
  checkIcon.className = 'task-checkbox-icon';
  checkIcon.textContent = '✓';
  checkbox.appendChild(checkIcon);

  const content = document.createElement('div');
  content.className = 'task-content';

  const titleEl = document.createElement('div');
  titleEl.className = 'task-title';
  titleEl.textContent = task.title;

  content.appendChild(titleEl);

  if (task.due_date) {
    const dueEl = document.createElement('div');
    dueEl.className = 'task-due';
    dueEl.textContent = formatDueDate(task.due_date, task.is_overdue);
    content.appendChild(dueEl);
  }

  el.appendChild(checkbox);
  el.appendChild(content);

  return el;
}

function renderTasks(tasks, listId) {
  const list = document.getElementById(listId);
  list.innerHTML = '';

  if (tasks.length === 0) {
    list.innerHTML = '<div class="empty-state">タスクはありません</div>';
    return;
  }

  for (const task of tasks) {
    list.appendChild(createTaskElement(task));
  }
}

// ===== 学校配布物 提案 =====
let currentProposals = [];
let currentProposalIndex = 0;

const CHILD_COLORS = {
  '紗奈': '#9b59b6',
  '和花': '#27ae60',
  '舞':   '#e67e22',
};

function openProposalsModal() {
  if (currentProposals.length === 0) return;
  currentProposalIndex = 0;
  renderProposalCard();
  document.getElementById('proposals-overlay').classList.remove('hidden');
}

function closeProposalsModal() {
  document.getElementById('proposals-overlay').classList.add('hidden');
}

function renderProposalCard() {
  const proposal = currentProposals[currentProposalIndex];
  const counter = document.getElementById('proposals-counter');
  counter.textContent = `${currentProposalIndex + 1} / ${currentProposals.length}`;

  const card = document.getElementById('proposals-card');
  const color = CHILD_COLORS[proposal.child_name] || '#888';
  const dateStr = proposal.event_date.replace(/-/g, '/');
  const timeStr = proposal.time_start
    ? (proposal.time_end ? `${proposal.time_start}〜${proposal.time_end}` : proposal.time_start)
    : '終日';

  card.innerHTML = `
    <div class="proposal-child-badge" style="background:${color}">${proposal.child_name}</div>
    <div class="proposal-event-title">${proposal.title}</div>
    <div class="proposal-meta">
      <span class="proposal-date">📅 ${dateStr}</span>
      <span class="proposal-time">🕐 ${timeStr}</span>
    </div>
    ${proposal.location ? `<div class="proposal-location">📍 ${proposal.location}</div>` : ''}
    ${proposal.description ? `<div class="proposal-desc">${proposal.description}</div>` : ''}
    ${proposal.image_filename ? `<div class="proposal-source">配布物: ${proposal.image_filename}</div>` : ''}
  `;
}

async function handleProposalAction(action) {
  const proposal = currentProposals[currentProposalIndex];
  const endpoint = `/api/proposals/${proposal.id}/${action}`;

  try {
    await fetch(endpoint, {
      method: 'POST',
      headers: authHeaders(),
    });
  } catch (e) {
    showStatusBanner('処理に失敗しました', 'error');
    setTimeout(hideStatusBanner, 3000);
    return;
  }

  // 次の提案へ or モーダルを閉じる
  currentProposals.splice(currentProposalIndex, 1);
  if (currentProposals.length === 0) {
    closeProposalsModal();
    updateProposalsBadge();
  } else {
    if (currentProposalIndex >= currentProposals.length) {
      currentProposalIndex = currentProposals.length - 1;
    }
    renderProposalCard();
  }
}

function updateProposalsBadge() {
  const badge = document.getElementById('proposals-badge');
  if (currentProposals.length > 0) {
    badge.textContent = `📄 ${currentProposals.length}`;
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

function syncProposals(proposals) {
  currentProposals = proposals || [];
  updateProposalsBadge();
}

document.getElementById('btn-approve').addEventListener('click', () => handleProposalAction('approve'));
document.getElementById('btn-reject').addEventListener('click', () => handleProposalAction('reject'));
document.getElementById('proposals-badge').addEventListener('click', openProposalsModal);
document.getElementById('proposals-overlay').addEventListener('click', (e) => {
  if (e.target === document.getElementById('proposals-overlay')) closeProposalsModal();
});

// ===== 天気描画 =====
function formatTempDelta(d) {
  if (d === null || d === undefined) return '';      // 前日データなし
  if (d > 0) return `<span class="temp-delta up">(+${d}度)</span>`;
  if (d < 0) return `<span class="temp-delta down">(${d}度)</span>`;  // d は既に「−」付き
  return '<span class="temp-delta flat">(±0度)</span>';
}

function renderWeather(weather) {
  const emojiEl     = document.getElementById('weather-emoji');
  const conditionEl = document.getElementById('weather-condition');
  const tempEl      = document.getElementById('weather-temp');
  const hourlyEl    = document.getElementById('weather-hourly');

  if (!weather) {
    emojiEl.textContent     = '—';
    conditionEl.textContent = '取得中…';
    tempEl.innerHTML        = '';
    hourlyEl.innerHTML      = '';
    return;
  }

  emojiEl.textContent     = weather.condition_emoji;
  conditionEl.textContent = weather.condition;
  // 前日比 (+N度 / -N度 / ±0度) を気温の後ろに添える
  tempEl.innerHTML =
    `↑${weather.temp_max}°${formatTempDelta(weather.temp_max_delta)} ` +
    `↓${weather.temp_min}°${formatTempDelta(weather.temp_min_delta)}`;

  hourlyEl.innerHTML = '';
  for (const h of weather.hourly_precip) {
    const p = h.precip_prob;
    const level = p >= 60 ? 'high' : p >= 30 ? 'mid' : p >= 10 ? 'low' : 'none';

    const block = document.createElement('div');
    block.className = 'precip-block';
    block.innerHTML = `
      <div class="precip-time">${h.label}</div>
      <div class="precip-pct ${level}">${p}%</div>
    `;
    hourlyEl.appendChild(block);
  }
}

// ===== 統合描画 =====
function renderAll(data) {
  updateDateDisplay(data);
  renderWeather(data.weather || null);
  renderEvents(data.events);
  renderTasks(data.stock_tasks, 'stock-list');
  renderTasks(data.flow_tasks, 'flow-list');
  document.getElementById('flow-title').textContent = `🔄 ${data.weekday}のタスク`;
  syncProposals(data.proposals || []);
}

// ===== 曜日タスク設定モーダル =====
const WEEKDAY_LABELS = ['月', '火', '水', '木', '金', '土', '日'];
let _todayWeekday = new Date().getDay(); // 0=日〜6=土（JS）→ JStoJA で変換
// JS: 0=日,1=月,...,6=土  /  Python: 0=月,...,6=日
function jsDayToJa(jsDay) { return jsDay === 0 ? 6 : jsDay - 1; }

function buildDaySelector(containerId, selectedDays = []) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';
  const todayJa = jsDayToJa(new Date().getDay());
  WEEKDAY_LABELS.forEach((label, i) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'day-toggle' + (selectedDays.includes(i) ? ' selected' : '') + (i === todayJa ? ' today-mark' : '');
    btn.textContent = label;
    btn.dataset.day = i;
    btn.addEventListener('click', () => btn.classList.toggle('selected'));
    container.appendChild(btn);
  });
}

function getSelectedDays(containerId) {
  return [...document.querySelectorAll(`#${containerId} .day-toggle.selected`)]
    .map(b => parseInt(b.dataset.day));
}

function renderDayChips(weekdays) {
  const todayJa = jsDayToJa(new Date().getDay());
  return WEEKDAY_LABELS.map((label, i) => {
    if (!weekdays.includes(i)) return '';
    const cls = i === todayJa ? 'day-chip today' : 'day-chip active';
    return `<span class="${cls}">${label}</span>`;
  }).join('');
}

async function loadWeeklyTasks() {
  const res = await fetch('/api/weekly-tasks', { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}

function renderWeeklyTaskList(tasks) {
  const list = document.getElementById('weekly-task-list');
  list.innerHTML = '';

  if (tasks.length === 0) {
    list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-secondary);font-size:0.9rem">まだ曜日タスクがありません</div>';
    return;
  }

  tasks.forEach(task => {
    const row = document.createElement('div');
    row.className = 'weekly-task-row';
    row.dataset.taskId = task.id;

    // 表示モード
    const display = document.createElement('div');
    display.className = 'weekly-task-display';
    display.innerHTML = `
      <span class="weekly-task-title">${escapeHtml(task.title)}</span>
      <div class="weekly-task-days">${renderDayChips(task.weekdays)}</div>
      <div class="weekly-task-actions">
        <button class="weekly-btn edit-btn">✏</button>
        <button class="weekly-btn delete delete-btn">🗑</button>
      </div>`;

    // 編集フォーム（初期は非表示）
    const editForm = document.createElement('div');
    editForm.className = 'weekly-task-edit';
    editForm.style.display = 'none';
    const editSelectorId = `edit-days-${task.id}`;
    editForm.innerHTML = `
      <input type="text" class="edit-title-input" value="${escapeHtml(task.title)}" maxlength="50">
      <div id="${editSelectorId}" class="day-selector"></div>
      <div class="weekly-edit-actions">
        <button class="weekly-cancel-btn">キャンセル</button>
        <button class="weekly-save-btn">保存</button>
      </div>`;

    row.appendChild(display);
    row.appendChild(editForm);
    list.appendChild(row);

    // 編集ボタン
    display.querySelector('.edit-btn').addEventListener('click', () => {
      display.style.display = 'none';
      editForm.style.display = 'flex';
      editForm.style.flexDirection = 'column';
      buildDaySelector(editSelectorId, task.weekdays);
      editForm.querySelector('.edit-title-input').focus();
    });

    // キャンセル
    editForm.querySelector('.weekly-cancel-btn').addEventListener('click', () => {
      editForm.style.display = 'none';
      display.style.display = 'flex';
    });

    // 保存
    editForm.querySelector('.weekly-save-btn').addEventListener('click', async () => {
      const title = editForm.querySelector('.edit-title-input').value.trim();
      const days = getSelectedDays(editSelectorId);
      if (!title || days.length === 0) return;
      const res = await fetch(`/api/weekly-tasks/${task.id}`, {
        method: 'PUT',
        headers: authHeaders(true),
        body: JSON.stringify({ title, weekdays: days }),
      });
      if (res.ok) {
        const updated = await loadWeeklyTasks();
        renderWeeklyTaskList(updated);
      }
    });

    // 削除
    display.querySelector('.delete-btn').addEventListener('click', async () => {
      if (!confirm(`「${task.title}」を削除しますか？`)) return;
      const res = await fetch(`/api/weekly-tasks/${task.id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      if (res.ok) {
        const updated = await loadWeeklyTasks();
        renderWeeklyTaskList(updated);
      }
    });
  });
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function openWeeklyModal() {
  document.getElementById('weekly-overlay').classList.remove('hidden');
  buildDaySelector('weekly-add-days');
  document.getElementById('weekly-add-title').value = '';
  document.getElementById('weekly-add-btn').disabled = true;
  const tasks = await loadWeeklyTasks();
  renderWeeklyTaskList(tasks);
}

function closeWeeklyModal() {
  document.getElementById('weekly-overlay').classList.add('hidden');
}

document.getElementById('weekly-settings-btn').addEventListener('click', openWeeklyModal);
document.getElementById('weekly-close-btn').addEventListener('click', closeWeeklyModal);
document.getElementById('weekly-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('weekly-overlay')) closeWeeklyModal();
});

// 追加フォーム
const addTitleInput = document.getElementById('weekly-add-title');
const addBtn = document.getElementById('weekly-add-btn');

addTitleInput.addEventListener('input', () => {
  addBtn.disabled = !addTitleInput.value.trim();
});

addBtn.addEventListener('click', async () => {
  const title = addTitleInput.value.trim();
  const days = getSelectedDays('weekly-add-days');
  if (!title || days.length === 0) {
    showStatusBanner('タスク名と曜日を入力してください', 'warning');
    setTimeout(hideStatusBanner, 2000);
    return;
  }
  const res = await fetch('/api/weekly-tasks', {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ title, weekdays: days }),
  });
  if (res.ok) {
    addTitleInput.value = '';
    addBtn.disabled = true;
    buildDaySelector('weekly-add-days');
    const updated = await loadWeeklyTasks();
    renderWeeklyTaskList(updated);
  }
});

// ===== 週間予定モーダル =====
async function openWeekModal() {
  const overlay = document.getElementById('week-overlay');
  overlay.classList.remove('hidden');

  const loading = document.getElementById('week-loading');
  const container = document.getElementById('week-days');
  loading.style.display = 'block';
  loading.textContent = '読み込み中…';
  container.innerHTML = '';

  try {
    const res = await fetch('/api/week', { headers: authHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderWeek(data);
    loading.style.display = 'none';
  } catch (e) {
    loading.textContent = '予定の取得に失敗しました';
  }
}

function closeWeekModal() {
  document.getElementById('week-overlay').classList.add('hidden');
}

function renderWeek(data) {
  const container = document.getElementById('week-days');
  container.innerHTML = '';

  for (const day of data.days) {
    const d = new Date(day.date + 'T00:00:00');
    const jsDay = d.getDay(); // 0=日, 6=土

    // 色分け: 祝日・日曜→赤、土曜→青（当日表示と同じルール）
    let dayClass = '';
    if (day.is_holiday || jsDay === 0) dayClass = 'holiday';
    else if (jsDay === 6) dayClass = 'saturday';

    const col = document.createElement('div');
    col.className = 'week-day' + (day.is_today ? ' today' : '');

    const head = document.createElement('div');
    head.className = 'week-day-head';
    const wd = day.weekday.replace('曜日', '');
    head.innerHTML = `
      <span class="week-day-date ${dayClass}">${d.getMonth() + 1}/${d.getDate()}（${wd}）</span>
      ${day.is_today ? '<span class="week-today-badge">今日</span>' : ''}
      ${day.holiday_name ? `<span class="week-holiday">${escapeHtml(day.holiday_name)}</span>` : ''}
    `;
    col.appendChild(head);

    const evWrap = document.createElement('div');
    evWrap.className = 'week-day-events';
    if (day.events.length === 0) {
      evWrap.innerHTML = '<div class="week-empty">予定なし</div>';
    } else {
      for (const ev of day.events) {
        const row = document.createElement('div');
        row.className = 'week-event';
        const dot = document.createElement('span');
        dot.className = 'week-event-dot';
        dot.style.background = ev.color;
        const time = document.createElement('span');
        time.className = 'week-event-time';
        time.textContent = ev.is_all_day ? '終日' : ev.start_time;
        const title = document.createElement('span');
        title.className = 'week-event-title';
        title.textContent = ev.title;
        row.appendChild(dot);
        row.appendChild(time);
        row.appendChild(title);
        evWrap.appendChild(row);
      }
    }
    col.appendChild(evWrap);
    container.appendChild(col);
  }
}

document.getElementById('week-view-btn').addEventListener('click', openWeekModal);
document.getElementById('week-close-btn').addEventListener('click', closeWeekModal);
document.getElementById('week-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('week-overlay')) closeWeekModal();
});

// ===== タップ処理（重複排除付き） =====
const pendingRequests = new Map();

async function handleTaskTap(el, task) {
  // 同一タスクへの進行中リクエストをキャンセル
  if (pendingRequests.has(task.id)) {
    pendingRequests.get(task.id).abort();
  }

  const controller = new AbortController();
  pendingRequests.set(task.id, controller);

  const isCompleted = el.classList.contains('completed');
  // task.id は "x-apple-reminder://UUID" のようにスラッシュを含むため URL には載せず、
  // 必ずボディで送る（パスに含めると 404 になり完了が記録されない）。
  const endpoint = isCompleted ? '/api/tasks/uncomplete' : '/api/tasks/complete';

  // 楽観的 UI 更新
  if (isCompleted) {
    el.classList.remove('completed');
  } else {
    el.classList.add('completed');
  }

  try {
    const body = isCompleted
      ? JSON.stringify({ task_id: task.id })
      : JSON.stringify({ task_id: task.id, task_type: task.task_type, due_date: task.due_date || null });

    await fetch(endpoint, {
      method: 'POST',
      headers: authHeaders(true),
      body: body,
      signal: controller.signal,
    });
  } catch (e) {
    if (e.name !== 'AbortError') {
      // 失敗したらロールバック
      if (isCompleted) {
        el.classList.add('completed');
      } else {
        el.classList.remove('completed');
      }
      showStatusBanner('タスク更新に失敗しました', 'error');
      setTimeout(hideStatusBanner, 3000);
    }
  } finally {
    pendingRequests.delete(task.id);
  }
}

// ===== イベントデリゲーション =====
for (const listId of ['stock-list', 'flow-list']) {
  document.getElementById(listId).addEventListener('click', (e) => {
    const item = e.target.closest('.task-item');
    if (!item) return;
    const task = {
      id: item.dataset.taskId,
      task_type: item.dataset.taskType,
      due_date: item.dataset.dueDate || null,
    };
    handleTaskTap(item, task);
  });
}

// ===== SSE接続 =====
let eventSource = null;

function connectSSE() {
  if (eventSource) {
    eventSource.close();
  }

  const url = API_TOKEN ? `/api/stream?token=${encodeURIComponent(API_TOKEN)}` : '/api/stream';
  eventSource = new EventSource(url);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      renderAll(data);
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
// 夜間(21:30–06:00)は Wake Lock を解放する。Mac側のADBスケジュールで画面を
// スリープさせるため、ここで画面を起こし続けると喧嘩してしまう。日中のみ保持する。
const NIGHT_START_MIN = 21 * 60 + 30; // 21:30
const NIGHT_END_MIN   = 6 * 60;       // 06:00

function isNightNow() {
  const n = new Date();
  const m = n.getHours() * 60 + n.getMinutes();
  return m >= NIGHT_START_MIN || m < NIGHT_END_MIN; // 跨ぎ（21:30〜翌6:00）
}

let wakeLockSentinel = null;

async function acquireWakeLock() {
  if (wakeLockSentinel) return;
  try {
    wakeLockSentinel = await navigator.wakeLock.request('screen');
    // OSが解放した場合（画面OFF等）に参照を戻し、日中なら再取得できるようにする
    wakeLockSentinel.addEventListener('release', () => { wakeLockSentinel = null; });
  } catch (_) { /* 非対応ブラウザでは無視 */ }
}

async function releaseWakeLock() {
  try { if (wakeLockSentinel) await wakeLockSentinel.release(); } catch (_) { /* noop */ }
  wakeLockSentinel = null;
}

// 可視かつ日中のときだけ画面を起こし続ける。夜間・非表示時は解放。
function manageWakeLock() {
  if (document.visibilityState !== 'visible' || isNightNow()) {
    releaseWakeLock();
  } else {
    acquireWakeLock();
  }
}

document.addEventListener('visibilitychange', () => {
  manageWakeLock();
  if (document.visibilityState === 'visible') {
    // SSE接続が切れていたら再接続
    if (!eventSource || eventSource.readyState === EventSource.CLOSED) {
      connectSSE();
    }
  }
});

// 時刻が夜間境界をまたいだら自動で取得/解放を切り替える（毎分判定）
setInterval(manageWakeLock, 60 * 1000);
manageWakeLock();

// ===== 定期リロード（保険・1日1回 深夜帯）=====
// データはSSE(/api/stream)で常時更新されるため、中身の最新化目的のリロードは不要。
// JSのメモリリーク・描画フリーズ・デプロイ後のSW更新ズレからの自動復帰が目的。
// 誰も見ていない早朝(4:00台)に1日1回だけ全リロードする。
// リロード後にタイマーが再起動して同一時間帯で多重発火するのを防ぐため、
// localStorageに実施日を記録して「その日もう実施済みか」をガードする。
const RELOAD_HOUR = 4; // リロードを実施する時刻（時）
setInterval(() => {
  const now = new Date();
  if (now.getHours() !== RELOAD_HOUR) return;
  const today = now.toISOString().slice(0, 10); // YYYY-MM-DD
  if (localStorage.getItem('lastDailyReload') === today) return;
  localStorage.setItem('lastDailyReload', today);
  window.location.reload();
}, 60 * 1000); // 1分ごとに時刻チェック

// ===== 初期化 =====
connectSSE();
