// Service Worker for Chattrix Push Notifications
// Handles push notification events and background message sync

const CACHE_NAME = 'chattrix-v1';
const NOTIFICATION_ICON = '/static/profile_pics/default.jpg';

// Install event
self.addEventListener('install', event => {
    console.log('📦 Service Worker installing...');
    self.skipWaiting();
});

// Activate event
self.addEventListener('activate', event => {
    console.log('✅ Service Worker activated');
    event.waitUntil(self.clients.claim());
});

// Push event - handles incoming push notifications
self.addEventListener('push', event => {
    console.log('📬 Push notification received:', event);
    
    if (event.data) {
        try {
            const data = event.data.json();
            console.log('📄 Push data:', data);
            
            const options = {
                body: data.body || 'New message in Chattrix',
                icon: data.icon || NOTIFICATION_ICON,
                badge: data.badge || NOTIFICATION_ICON,
                tag: 'chattrix-notification',
                data: {
                    url: data.url || '/chat',
                    timestamp: Date.now()
                },
                actions: [
                    {
                        action: 'view',
                        title: 'View Message',
                        icon: NOTIFICATION_ICON
                    },
                    {
                        action: 'dismiss',
                        title: 'Dismiss'
                    }
                ],
                requireInteraction: false,
                vibrate: [200, 100, 200],
                silent: false
            };
            
            event.waitUntil(
                self.registration.showNotification(
                    data.title || 'Chattrix',
                    options
                )
            );
            
        } catch (error) {
            console.error('❌ Error parsing push data:', error);
            
            // Fallback notification
            event.waitUntil(
                self.registration.showNotification('Chattrix', {
                    body: 'You have a new message',
                    icon: NOTIFICATION_ICON,
                    badge: NOTIFICATION_ICON,
                    tag: 'chattrix-notification',
                    data: { url: '/chat' }
                })
            );
        }
    } else {
        console.warn('⚠️ Push event with no data');
        
        // Fallback notification when no data
        event.waitUntil(
            self.registration.showNotification('Chattrix', {
                body: 'You have a new message',
                icon: NOTIFICATION_ICON,
                badge: NOTIFICATION_ICON,
                tag: 'chattrix-notification',
                data: { url: '/chat' }
            })
        );
    }
});

// Notification click event
self.addEventListener('notificationclick', event => {
    console.log('🖱️ Notification clicked:', event.notification);
    
    event.notification.close();
    
    const url = event.notification.data?.url || '/chat';
    
    if (event.action === 'view' || !event.action) {
        // Open or focus the chat page
        event.waitUntil(
            clients.matchAll({ type: 'window' }).then(clientList => {
                // Check if Chattrix is already open
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        client.focus();
                        client.navigate(url);
                        return;
                    }
                }
                
                // Open new window if not already open
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
        );
    } else if (event.action === 'dismiss') {
        // Just close the notification (already closed above)
        console.log('🚫 Notification dismissed');
    }
});

// Background sync for offline messages (future enhancement)
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        console.log('🔄 Background sync triggered');
        // Handle background message sync when back online
    }
});

// Error handling
self.addEventListener('error', event => {
    console.error('❌ Service Worker error:', event.error);
});

self.addEventListener('unhandledrejection', event => {
    console.error('❌ Service Worker unhandled promise rejection:', event.reason);
});
