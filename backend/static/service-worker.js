const CACHE_NAME = "leftover-wizard-v1";

// 你可以把這些路徑換成你實際路由（例如 /dashboard/1）
const PRECACHE_URLS = [
  "/",
  "/static/manifest.json",
  "/service-worker.js",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/icon-512-maskable.png"
];


self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)))
    )
  );
  self.clients.claim();
});

// 基本策略：
// - 對 GET：先走網路，失敗再用快取（適合 API/動態頁面）
// - 你也可以改成對 HTML 用 cache-first
self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  event.respondWith(
    fetch(req)
      .then((res) => {
        // 網路成功就更新快取（僅同源且可快取的資源）
        const url = new URL(req.url);
        if (url.origin === self.location.origin) {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, resClone));
        }
        return res;
      })
      .catch(() => caches.match(req).then((cached) => cached || new Response("離線中，且尚未快取此資源。", { status: 503 })))
  );
});
