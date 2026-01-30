// Offline App Initialization - Initialize all offline components on page load
class OfflineAppInitializer {
  static async init() {
    console.log('Initializing offline app support...');

    try {
      // Wait for database to be ready
      await offlineDB.ready();
      console.log('Offline database initialized');
      // If logout triggered cache clear, handle it now (do not clear before logout POST)
      await this.handleClearOnLogout();

      // Initialize UI manager
      console.log('Initializing UI components');

      // Start periodic sync if online
      if (syncManager.isOnline) {
        syncManager.startPeriodicSync(60000); // Sync every 60 seconds
        console.log('Periodic sync started');
      }

      // Register default conflict handlers
      this.registerDefaultConflictHandlers();

      // Load user context from authentication
      await this.initializeUserContext();

      // Load initial data
      await this.loadInitialData();

      // Set up service worker if available
      if ('serviceWorker' in navigator) {
        this.setupServiceWorker();
      }

      console.log('Offline app initialization complete');
      this.dispatchInitializationComplete();

    } catch (error) {
      console.error('Error initializing offline app:', error);
      // App can still work without full offline support
    }
  }

  static async handleClearOnLogout() {
    try {
      const flag = sessionStorage.getItem('clearOnLogout');
      if (!flag) return;
      console.log('Detected logout cache-clear flag; clearing offline caches...');

      // Clear IndexedDB
      try {
        if (window.offlineDB) await window.offlineDB.clearAllData();
      } catch (err) {
        console.warn('Failed to clear IndexedDB during logout cleanup:', err);
      }

      // Clear service worker caches
      try {
        if ('caches' in window) {
          const cacheNames = await caches.keys();
          await Promise.all(cacheNames.map(name => caches.delete(name)));
        }
      } catch (err) {
        console.warn('Failed to clear service worker caches during logout cleanup:', err);
      }

      // Clear localStorage keys related to auth/offline
      try {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('authtoken');
        localStorage.removeItem('user_context');
        localStorage.removeItem('currentUser');
        Object.keys(localStorage).forEach(key => {
          if (key.includes('sync') || key.includes('offline') || key.includes('user') || key.includes('school')) {
            localStorage.removeItem(key);
          }
        });
      } catch (err) {
        console.warn('Failed to clear localStorage during logout cleanup:', err);
      }

      // Clear sessionStorage flag and all session storage
      try {
        sessionStorage.removeItem('clearOnLogout');
        sessionStorage.clear();
      } catch (err) {
        console.warn('Failed to clear sessionStorage during logout cleanup:', err);
      }

      // Unregister service workers
      try {
        if ('serviceWorker' in navigator) {
          const regs = await navigator.serviceWorker.getRegistrations();
          for (const r of regs) await r.unregister();
        }
      } catch (err) {
        console.warn('Failed to unregister service workers during logout cleanup:', err);
      }

      console.log('Logout cache cleanup complete');
    } catch (err) {
      console.error('Error in handleClearOnLogout:', err);
    }
  }

  static async initializeUserContext() {
    try {
      // Get user info from page (assuming it's in a data attribute or global)
      const userContext = this.extractUserContext();
      
      if (userContext) {
        await offlineDB.setUserContext(userContext);
        console.log('User context stored:', userContext.username);
      }
    } catch (error) {
      console.warn('Could not initialize user context:', error);
    }
  }

  static extractUserContext() {
    // Try multiple ways to get user context
    
    // Method 1: From meta tags
    const userMeta = document.querySelector('meta[name="user-id"]');
    const schoolMeta = document.querySelector('meta[name="school-id"]');
    const tokenMeta = document.querySelector('meta[name="auth-token"]');
    
    if (userMeta || schoolMeta) {
      return {
        userId: parseInt(userMeta?.content || '0'),
        schoolId: parseInt(schoolMeta?.content || '0'),
        token: tokenMeta?.content || null,
        timestamp: Date.now()
      };
    }

    // Method 2: From global window object
    if (window.currentUser) {
      return {
        userId: window.currentUser.id,
        username: window.currentUser.username,
        schoolId: window.currentUser.school_id,
        role: window.currentUser.role,
        token: window.currentUser.token || this.getAuthToken(),
        timestamp: Date.now()
      };
    }

    // Method 3: Extract from JWT token if available
    const token = this.getAuthToken();
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return {
          userId: payload.user_id || payload.sub,
          username: payload.username,
          schoolId: payload.school_id,
          token: token,
          timestamp: Date.now()
        };
      } catch (e) {
        // Invalid token format
      }
    }

    return null;
  }

  static getAuthToken() {
    // Try multiple locations for auth token
    
    // 1. From localStorage
    let token = localStorage.getItem('auth_token');
    if (token) return token;

    // 2. From sessionStorage
    token = sessionStorage.getItem('auth_token');
    if (token) return token;

    // 3. From cookie
    const name = 'authtoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [key, value] = cookie.trim().split('=');
      if (key === name) return value;
    }

    return null;
  }

  static async loadInitialData() {
    try {
      // Check if we already have cached data. Honor refresh flag in URL to force fetch.
      const urlParams = new URLSearchParams(window.location.search);
      const forceRefresh = urlParams.get('refresh') === '1';
      const schools = await offlineDB.getAll('schools');
      if (schools.length > 0 && !forceRefresh) {
        console.log('Using cached data:', schools.length, 'schools');
        return;
      }

      // If online and no cache, fetch initial data
      if (syncManager.isOnline) {
        console.log('Fetching initial offline data...');
        const userContext = await offlineDB.getUserContext();
        if (!userContext || !userContext.token) {
          console.warn('Cannot fetch data without auth token');
          return;
        }

        // Fetch all necessary data
        const models = [
          'schools', 'users', 'classSections', 'subjects', 
          'gradingScales', 'gradingPeriods', 'studentEnrollments',
          'grades', 'attendance'
        ];

        for (const model of models) {
          try {
            const response = await fetch(`/api/${this.pluralizeModel(model)}/`, {
              headers: {
                'Authorization': `Bearer ${userContext.token}`
              }
            });

            if (response.ok) {
              let data = await response.json();
              
              // Handle paginated responses
              if (data.results && Array.isArray(data.results)) {
                data = data.results;
              } else if (!Array.isArray(data)) {
                data = [data];
              }

              if (Array.isArray(data) && data.length > 0) {
                await offlineDB.putBatch(model, data);
                console.log(`Cached ${data.length} items for ${model}`);
              }
            }
          } catch (error) {
            console.warn(`Could not fetch ${model}:`, error);
          }
        }

        // Update last sync time
        await offlineDB.setLastSyncTime(new Date());
      }
    } catch (error) {
      console.warn('Error loading initial data:', error);
    }
  }

  static pluralizeModel(model) {
    const plural = {
      'classSections': 'class-sections',
      'gradingScales': 'grading-scales',
      'gradingPeriods': 'grading-periods',
      'studentEnrollments': 'student-enrollments'
    };
    return plural[model] || model + 's';
  }

  static registerDefaultConflictHandlers() {
    // Register handlers for each model type
    
    // Grades: Local wins (teacher's entry)
    syncManager.registerConflictHandler('grades', async (conflict) => {
      console.log('Resolving grade conflict:', conflict);
      return 'keep-local'; // Keep local teacher entry
    });

    // Attendance: Merge strategy (keep both with timestamps)
    syncManager.registerConflictHandler('attendance', async (conflict) => {
      console.log('Resolving attendance conflict:', conflict);
      return 'merge'; // Let merge logic handle it
    });

    // Report Cards: Server wins (published official record)
    syncManager.registerConflictHandler('reportcards', async (conflict) => {
      console.log('Resolving report card conflict:', conflict);
      return 'keep-server';
    });
  }

  static setupServiceWorker() {
    navigator.serviceWorker.register('/sw.js')
      .then(registration => {
        console.log('Service Worker registered:', registration);
        
        // Check for updates periodically
        setInterval(() => {
          registration.update();
        }, 60000); // Check every minute
      })
      .catch(error => {
        console.warn('Service Worker registration failed:', error);
      });
  }

  static dispatchInitializationComplete() {
    const event = new CustomEvent('offline:app-initialized', {
      detail: { timestamp: Date.now() }
    });
    window.dispatchEvent(event);
  }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    OfflineAppInitializer.init();
  });
} else {
  OfflineAppInitializer.init();
}
