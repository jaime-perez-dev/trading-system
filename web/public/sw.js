// EdgeSignals Service Worker for Push Notifications

const CACHE_NAME = "edgesignals-v1";

// Install event
self.addEventListener("install", (event) => {
  console.log("[SW] Installing service worker");
  self.skipWaiting();
});

// Activate event
self.addEventListener("activate", (event) => {
  console.log("[SW] Activating service worker");
  event.waitUntil(clients.claim());
});

// Push event - handle incoming push notifications
self.addEventListener("push", (event) => {
  console.log("[SW] Push received");
  
  let data = {
    title: "EdgeSignals Alert",
    body: "New trading signal detected!",
    icon: "/icon-192.png",
    badge: "/badge-72.png",
    tag: "signal",
    data: {},
  };
  
  try {
    if (event.data) {
      const payload = event.data.json();
      data = { ...data, ...payload };
    }
  } catch (e) {
    console.error("[SW] Error parsing push data:", e);
    if (event.data) {
      data.body = event.data.text();
    }
  }
  
  const options = {
    body: data.body,
    icon: data.icon || "/icon-192.png",
    badge: data.badge || "/badge-72.png",
    tag: data.tag || "signal",
    data: data.data || {},
    vibrate: [200, 100, 200],
    requireInteraction: true,
    actions: [
      { action: "view", title: "View Signal" },
      { action: "dismiss", title: "Dismiss" },
    ],
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click event
self.addEventListener("notificationclick", (event) => {
  console.log("[SW] Notification clicked:", event.action);
  
  event.notification.close();
  
  if (event.action === "dismiss") {
    return;
  }
  
  // Open dashboard on click
  const urlToOpen = event.notification.data?.url || "/dashboard";
  
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true })
      .then((windowClients) => {
        // Check if there's already a window open
        for (const client of windowClients) {
          if (client.url.includes("/dashboard") && "focus" in client) {
            return client.focus();
          }
        }
        // Open new window if none found
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Notification close event
self.addEventListener("notificationclose", (event) => {
  console.log("[SW] Notification closed");
});

// Background sync for offline signal updates
self.addEventListener("sync", (event) => {
  if (event.tag === "sync-signals") {
    console.log("[SW] Background sync: signals");
    event.waitUntil(syncSignals());
  }
});

async function syncSignals() {
  try {
    const response = await fetch("/api/signals?tier=pro&limit=10");
    if (response.ok) {
      console.log("[SW] Signals synced successfully");
    }
  } catch (e) {
    console.error("[SW] Sync failed:", e);
  }
}
