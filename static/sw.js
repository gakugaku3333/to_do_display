// ===== Service Worker =====
// ダッシュボードのオフライン対応とキャッシュ管理。
//
// キャッシュ戦略:
//   - ナビゲーション(/) と /static/js/* (ESモジュール一式) : network-first
//       → コード/HTML の更新を常に即反映。オフライン時のみキャッシュにフォールバック。
//   - その他の静的アセット(CSS/manifest/アイコン等) : stale-while-revalidate
//       → 表示は即座（キャッシュ）、裏で最新を取得して次回に反映。
//   - /api/stream (SSE) : SW を通さない（ストリームを途切れさせない）
//   - その他 /api/* : network-first
//
// 重要: 以前は全アセットが cache-first だったため、app.js を更新しても
// 古いコードが配信され続ける問題があった。コード系を network-first にして解消。
// app.js は Phase 1 で static/js/ 配下の ES Modules に分割された。

const CACHE_VERSION = 'v6';
const CACHE_NAME = `dashboard-${CACHE_VERSION}`;

// オフライン起動に最低限必要なアセット（依存モジュールは main.js の import で動的取得される）
const PRECACHE_URLS = [
  '/',
  '/static/style.css',
  '/static/js/main.js',
  '/static/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      // cache:'reload' でブラウザの HTTP キャッシュを迂回し、常にネットワークから取得する。
      // これにより Safari の旧キャッシュが SW の precache を汚染するのを防ぐ。
      Promise.all(
        PRECACHE_URLS.map((url) =>
          cache.add(new Request(url, { cache: 'reload' }))
        )
      )
    )
  );
  // 新しい SW を待機させずに即座に有効化する
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
        )
      )
      // 既存のタブを即座に新しい SW の管理下に置く
      .then(() => self.clients.claim())
  );
});

// ネットワーク優先。成功時はキャッシュを更新し、失敗時はキャッシュへフォールバック。
async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw err;
  }
}

// キャッシュを即返ししつつ、裏でネットワークから取得してキャッシュを更新。
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const networkFetch = fetch(request)
    .then((response) => {
      if (response && response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);
  return cached || networkFetch;
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 同一オリジン以外（Google Fonts 等）は介入しない
  if (url.origin !== self.location.origin) return;

  // SSE ストリームは SW を通さない
  if (url.pathname === '/api/stream') return;

  // API は network-first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // ナビゲーションと ESモジュール一式は network-first（コード更新を即反映）
  if (request.mode === 'navigate' || url.pathname.startsWith('/static/js/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // その他の静的アセットは stale-while-revalidate
  event.respondWith(staleWhileRevalidate(request));
});
