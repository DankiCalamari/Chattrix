self.addEventListener('push', function(event) {
    console.log('📥 Push event received:', event);
    
    if (event.data) {
        try {
            const data = event.data.json();
            console.log('📱 Push notification data:', data);
            
            const options = {
                body: data.body || data.message || 'New message received',
                icon: data.icon || '/static/profile_pics/default.jpg',
                badge: data.badge || '/static/profile_pics/default.jpg',
                tag: 'chattrix-message',
                data: {
                    url: data.url || '/chat'
                },
                actions: [
                    {
                        action: 'open',
                        title: 'Open Chat'
                    },
                    {
                        action: 'close',
                        title: 'Dismiss'
                    }
                ],
                requireInteraction: true,
                vibrate: [200, 100, 200]
            };

            event.waitUntil(
                self.registration.showNotification(data.title || 'New Message', options)
            );
        } catch (error) {
            console.error('❌ Error parsing push notification data:', error);
            
            // Fallback notification
            event.waitUntil(
                self.registration.showNotification('New Message', {
                    body: 'You have a new message in Chattrix',
                    icon: '/static/profile_pics/default.jpg',
                    tag: 'chattrix-message'
                })
            );
        }
    } else {
        console.log('📭 Push event received with no data');
        
        // Show generic notification
        event.waitUntil(
            self.registration.showNotification('New Message', {
                body: 'You have a new message in Chattrix',
                icon: '/static/profile_pics/default.jpg',
                tag: 'chattrix-message'
            })
        );
    }
});

self.addEventListener('notificationclick', function(event) {
    console.log('🖱️ Notification clicked:', event);
    event.notification.close();
    
    if (event.action === 'open' || !event.action) {
        const urlToOpen = event.notification.data?.url || '/chat';
        
        event.waitUntil(
            clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
                // Check if there's already a window/tab open with the target URL
                for (let client of clientList) {
                    if (client.url.includes(urlToOpen) && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                // If no existing window, open a new one
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
        );
    }
});

// Handle service worker installation
self.addEventListener('install', function(event) {
    console.log('⚙️ Service worker installing...');
    self.skipWaiting();
});

// Handle service worker activation
self.addEventListener('activate', function(event) {
    console.log('✅ Service worker activated');
    event.waitUntil(clients.claim());
});