"""PWA 渐进式 Web 应用支持（阶段11: 离线访问 + 移动安装）。

提供 PWA Manifest 和 Service Worker，让用户可以：
    - 将应用安装到手机/桌面主屏幕
    - 离线访问已加载的页面
    - 获得原生应用般的体验

核心功能：
    - ``get_manifest()``  → PWA Manifest JSON
    - ``get_service_worker()`` → Service Worker JavaScript

设计原则：
    - 第一性原理：Web 应用应能离线工作
    - 渐进增强：PWA 功能不影响基础体验
    - 缓存策略：静态资源缓存优先，API 请求网络优先
"""

from __future__ import annotations

import json


def get_manifest() -> str:
    """返回 PWA Manifest JSON。

    Returns:
        manifest.json 内容字符串
    """
    manifest = {
        "name": "GitHub Trending Audio",
        "short_name": "GH Audio",
        "description": "将 GitHub 热门项目转化为音频播客",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0d1117",
        "theme_color": "#161b22",
        "orientation": "any",
        "icons": [
            {
                "src": "/icon-512.jpg",
                "sizes": "512x512",
                "type": "image/jpeg",
                "purpose": "any maskable",
            },
            {
                "src": "/icon-512.jpg",
                "sizes": "192x192",
                "type": "image/jpeg",
                "purpose": "any",
            },
        ],
        "categories": ["productivity", "education"],
        "lang": "zh-CN",
    }
    return json.dumps(manifest, ensure_ascii=False, indent=2)


def get_service_worker() -> str:
    """返回 Service Worker JavaScript。

    缓存策略：
        - 静态页面（/）：缓存优先，回退网络
        - API 请求：网络优先，回退缓存
        - CDN 资源：缓存优先

    Returns:
        sw.js 内容字符串
    """
    return r"""// PWA Service Worker - GitHub Trending Audio
const CACHE_NAME = 'gh-trending-audio-v1';
const STATIC_ASSETS = [
  '/',
  '/dashboard',
  '/player',
  '/manifest.json',
  '/icon-512.jpg',
];

// CDN 资源缓存
const CDN_PATTERNS = [
  'cdn.jsdelivr.net',
  'unpkg.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com',
];

// 安装：预缓存静态资源
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_ASSETS).catch(function() {
        // 部分资源缓存失败不阻止安装
      });
    })
  );
  self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names.filter(function(name) { return name !== CACHE_NAME; })
             .map(function(name) { return caches.delete(name); })
      );
    })
  );
  self.clients.claim();
});

// 请求拦截
self.addEventListener('fetch', function(event) {
  const url = new URL(event.request.url);

  // 不拦截非 GET 请求
  if (event.request.method !== 'GET') return;

  // API 请求：网络优先，回退缓存
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, clone);
            });
          }
          return response;
        })
        .catch(function() {
          return caches.match(event.request);
        })
    );
    return;
  }

  // CDN 资源：缓存优先
  if (CDN_PATTERNS.some(function(p) { return url.hostname.includes(p); })) {
    event.respondWith(
      caches.match(event.request).then(function(cached) {
        return cached || fetch(event.request).then(function(response) {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, clone);
            });
          }
          return response;
        }).catch(function() { return cached; });
      })
    );
    return;
  }

  // 页面请求：缓存优先，回退网络
  event.respondWith(
    caches.match(event.request).then(function(cached) {
      return cached || fetch(event.request).then(function(response) {
        if (response.ok && event.request.mode === 'navigate') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      }).catch(function() {
        // 离线回退到缓存的首页
        return caches.match('/');
      });
    })
  );
);
"""


def get_pwa_meta_tags() -> str:
    """返回 PWA 相关的 HTML meta 标签。

    Returns:
        HTML meta 标签字符串，插入到 <head> 中
    """
    return """<link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#161b22">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="GH Audio">
    <link rel="apple-touch-icon" href="/icon-512.jpg">"""


def get_sw_registration_script() -> str:
    """返回 Service Worker 注册 JavaScript。

    Returns:
        JavaScript 代码字符串，插入到页面底部
    """
    return """<script>
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js').then(function(reg) {
            console.log('PWA Service Worker registered');
        }).catch(function(err) {
            console.log('SW registration failed:', err);
        });
    });
}
</script>"""
