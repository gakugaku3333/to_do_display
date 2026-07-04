// render(state): #weekly-progress のみを触る。
// 今日のチェック対象曜日タスクの完了率を星で表示する（ゲーミフィケーションは深追いせず、
// ポイント制などは持たない。曜日タスクが無い日は何も表示しない）。
export function render(state) {
  const el = document.getElementById('weekly-progress');
  if (!el) return;

  const data = state.data;
  const total = data ? data.weekly_total : 0;
  if (!total) {
    el.textContent = '';
    return;
  }

  const completed = data.weekly_completed;
  el.textContent = '★'.repeat(completed) + '☆'.repeat(total - completed);
}
