import { escapeHtml } from '../utils.js';

// render(state): #countdown-banner のみを触る。
// Googleカレンダーで「★」接頭辞を付けたイベント（例: "★運動会"）を、
// 一番近い予定だけ「あと◯日」として大きく表示する。設定UIは持たず命名規約で実現。
export function render(state) {
  const el = document.getElementById('countdown-banner');
  if (!el) return;

  const events = (state.data && state.data.countdown_events) || [];
  if (events.length === 0) {
    el.className = 'hidden';
    return;
  }

  const next = events[0];
  const daysText = next.days_until === 0 ? '今日です！' : `あと${next.days_until}日`;
  el.innerHTML = `🎏 <span class="countdown-title">${escapeHtml(next.title)}</span> まで <span class="countdown-days">${daysText}</span>`;
  el.className = '';
}
