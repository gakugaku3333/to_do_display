import { fetchWeek } from '../api.js';
import { dateColorClass, escapeHtml, dismissOnBackdrop } from '../utils.js';

function renderWeek(data) {
  const container = document.getElementById('week-days');
  container.innerHTML = '';

  for (const day of data.days) {
    const d = new Date(day.date + 'T00:00:00');
    const jsDay = d.getDay(); // 0=日, 6=土
    const dayClass = dateColorClass(jsDay, day.is_holiday);

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

async function openModal() {
  const overlay = document.getElementById('week-overlay');
  overlay.classList.remove('hidden');

  const loading = document.getElementById('week-loading');
  const container = document.getElementById('week-days');
  loading.style.display = 'block';
  loading.textContent = '読み込み中…';
  container.innerHTML = '';

  try {
    const data = await fetchWeek();
    renderWeek(data);
    loading.style.display = 'none';
  } catch (e) {
    loading.textContent = '予定の取得に失敗しました';
  }
}

function closeModal() {
  document.getElementById('week-overlay').classList.add('hidden');
}

export function initWeekModal() {
  document.getElementById('week-view-btn').addEventListener('click', openModal);
  document.getElementById('week-close-btn').addEventListener('click', closeModal);
  dismissOnBackdrop('week-overlay', closeModal);
}
