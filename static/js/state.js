// 単一の状態オブジェクト + subscribe/setState。
// SSE受信・APIレスポンスは全て setState に流し込むだけにし、購読側（各コンポーネント）が
// 自分のコンテナだけを再描画する。状態変更の経路を一本化することで、
// innerHTML による意図しない子要素破壊（過去の silent fail バグ）の再発を防ぐ。

let state = {
  data: null,       // 最新の TodayData（SSE経由）
  proposals: [],    // 学校配布物の承認待ち提案
};

const listeners = new Set();

export function getState() {
  return state;
}

export function setState(patch) {
  state = { ...state, ...patch };
  for (const fn of listeners) fn(state);
}

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
