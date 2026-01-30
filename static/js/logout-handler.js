// Logout Handler - Clear all offline data and caches on logout
class LogoutHandler {
  static async handleLogout() {
    console.log('Clearing all offline data on logout...');
    
    try {
      // 1. Clear IndexedDB
      await this.clearIndexedDB();
      
      // 2. Clear Service Worker cache
      await this.clearServiceWorkerCache();
      
      // 3. Clear localStorage
      this.clearLocalStorage();
      
      // 4. Clear sessionStorage
      this.clearSessionStorage();
      
      // 5. Clear cookies
      this.clearAuthCookies();
      
      // 6. Notify the server
      await this.notifyServerCacheClear();
      
      console.log('All offline caches cleared successfully');
    } catch (error) {
      console.error('Error during logout cache clearing:', error);
    }
  }

  static async clearIndexedDB() {
    try {
      if (window.offlineDB) {
        await window.offlineDB.clearAllData();
      }
    } catch (error) {
      console.warn('Failed to clear IndexedDB:', error);
    }
  }

  static async clearServiceWorkerCache() {
    try {
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(
          cacheNames.map(cacheName => caches.delete(cacheName))
        );
        console.log('Service Worker caches cleared');
      }
    } catch (error) {
      console.warn('Failed to clear Service Worker cache:', error);
    }
  }

  static clearLocalStorage() {
    try {
      // Clear auth tokens and sensitive data
      localStorage.removeItem('auth_token');
      localStorage.removeItem('authtoken');
      localStorage.removeItem('user_context');
      localStorage.removeItem('currentUser');
      localStorage.removeItem('sessionStorage');
      
      // Clear any sync-related data
      Object.keys(localStorage).forEach(key => {
        if (key.includes('sync') || key.includes('offline') || key.includes('user') || key.includes('school')) {
          localStorage.removeItem(key);
        }
      });
      
      console.log('LocalStorage cleared');
    } catch (error) {
      console.warn('Failed to clear localStorage:', error);
    }
  }

  static clearSessionStorage() {
    try {
      sessionStorage.clear();
      console.log('SessionStorage cleared');
    } catch (error) {
      console.warn('Failed to clear sessionStorage:', error);
    }
  }

  static clearAuthCookies() {
    try {
      const cookies = document.cookie.split(';');
      cookies.forEach(cookie => {
        const [name] = cookie.trim().split('=');
        if (name) {
          document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
        }
      });
      console.log('Cookies cleared');
    } catch (error) {
      console.warn('Failed to clear cookies:', error);
    }
  }

  static async notifyServerCacheClear() {
    try {
      await fetch('/api/clear-offline-cache/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          timestamp: new Date().toISOString()
        })
      });
      console.log('Server notified of cache clear');
    } catch (error) {
      console.warn('Failed to notify server:', error);
    }
  }

  // Unregister service workers
  static async unregisterServiceWorkers() {
    try {
      if ('serviceWorker' in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        registrations.forEach(registration => {
          registration.unregister();
        });
        console.log('Service workers unregistered');
      }
    } catch (error) {
      console.warn('Failed to unregister service workers:', error);
    }
  }
}

// Attach to window for global access
window.LogoutHandler = LogoutHandler;

// Auto-detect logout form submission
document.addEventListener('DOMContentLoaded', () => {
  const logoutForms = document.querySelectorAll('form[action*="logout"]');
  logoutForms.forEach(form => {
    form.addEventListener('submit', (e) => {
      // Don't clear caches before the POST — mark for clearing after redirect
      try {
        sessionStorage.setItem('clearOnLogout', '1');
      } catch (err) {
        console.warn('Could not set clearOnLogout flag:', err);
      }
      // allow normal form submission to proceed so CSRF token and session remain intact
    });
  });
});
