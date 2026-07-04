// render(state): #events-list のみを触る。
export function render(state) {
  const events = state.data ? state.data.events : [];
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
    timeEl.textContent = ev.is_all_day ? '' : ev.start_time;

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
