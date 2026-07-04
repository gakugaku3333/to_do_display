import { dateColorClass, escapeHtml } from '../utils.js';

// render(state): #date-info と #last-refresh のみを触る。
export function render(state) {
  const data = state.data;
  if (!data) return;

  const dateEl = document.getElementById('date-info');
  const d = new Date(data.date + 'T00:00:00');
  const year = d.getFullYear();
  const month = d.getMonth() + 1;
  const day = d.getDate();
  const jsDay = d.getDay(); // 0=日, 6=土
  const refreshText = data.last_refresh ? `更新 ${data.last_refresh}` : '';

  const dayClass = dateColorClass(jsDay, data.is_holiday);

  const holidayBadge = data.holiday_name
    ? `<span class="holiday-badge">${data.holiday_name}</span>`
    : '';

  const trashBadges = (data.trash_labels || [])
    .map((label) => `<span class="trash-badge">🗑️ ${escapeHtml(label)}</span>`)
    .join('');

  dateEl.innerHTML = `<span class="date-main ${dayClass}">${year}年${month}月${day}日（${data.weekday.replace('曜日', '')}）${holidayBadge}${trashBadges}</span>`;

  const refreshEl = document.getElementById('last-refresh');
  if (refreshEl) refreshEl.textContent = refreshText;
}
