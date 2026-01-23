// Service Worker for ReportCardApp PWA
const CACHE_NAME = 'schoolsync-v1';
const STATIC_CACHE = 'schoolsync-static-v1';
const DYNAMIC_CACHE = 'schoolsync-dynamic-v1';

// Assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/offline/',
  '/static/schools/css/bootstrap.min.css',
  '/static/schools/js/bootstrap.bundle.min.js',
  '/static/schools/css/style.css',
  '/static/schools/manifest.json',
  '/static/schools/images/icon-192.png',
  '/static/schools/images/icon-512.png'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  console.log('Service Worker: Installing');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Service Worker: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch(err => console.log('Service Worker: Caching failed', err))
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== STATIC_CACHE && cache !== DYNAMIC_CACHE) {
            console.log('Service Worker: Deleting old cache', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      caches.open(DYNAMIC_CACHE).then(async cache => {
        try {
          const response = await fetch(request);
          const responseClone = response.clone();

          // Cache successful API responses
          if (response.status === 200) {
            cache.put(request, responseClone);

            // Also cache in IndexedDB for offline access
            try {
              const data = await responseClone.json();
              if (data && typeof data === 'object') {
                // Determine model from URL
                const model = getModelFromUrl(url.pathname);
                if (model && Array.isArray(data)) {
                  await cacheData(model, data);
                } else if (model && data.id) {
                  await cacheData(model, [data]);
                }
              }
            } catch (e) {
              // Ignore JSON parsing errors
            }
          }

          return response;
        } catch (error) {
          // Return cached version if offline
          const cachedResponse = await cache.match(request);
          if (cachedResponse) {
            return cachedResponse;
          }

          // Try to return offline fallback for data requests
          return new Response(JSON.stringify({ error: 'Offline', message: 'Data not available offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          });
        }
      })
    );
    return;
  }

  // Handle static assets and pages
  event.respondWith(
    caches.match(request)
      .then(response => {
        if (response) {
          return response;
        }

        return fetch(request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Cache the response
            const responseToCache = response.clone();
            caches.open(DYNAMIC_CACHE)
              .then(cache => {
                cache.put(request, responseToCache);
              });

            return response;
          })
          .catch(() => {
            // Return offline fallback for pages
            if (request.destination === 'document') {
              return caches.match('/');
            }
          });
      })
  );
});

// Background sync for offline operations
self.addEventListener('sync', event => {
  console.log('Service Worker: Background sync', event.tag);

  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

// Periodic sync for regular data updates
self.addEventListener('periodicsync', event => {
  console.log('Service Worker: Periodic sync', event.tag);

  if (event.tag === 'periodic-data-sync') {
    event.waitUntil(doPeriodicSync());
  }
});

async function doBackgroundSync() {
  try {
    // Get pending operations from IndexedDB
    const pendingOps = await getPendingOperations();

    for (const op of pendingOps) {
      try {
        const response = await fetch(op.url, {
          method: op.method,
          headers: op.headers,
          body: op.body
        });

        if (response.ok) {
          // Remove from pending operations
          await removePendingOperation(op.id);
        }
      } catch (error) {
        console.log('Sync failed for operation:', op.id, error);
      }
    }
  } catch (error) {
    console.log('Background sync failed:', error);
  }
}

async function doPeriodicSync() {
  try {
    console.log('Service Worker: Performing periodic data sync');

    // Get stored user context
    const userContext = await getStoredUserContext();
    if (!userContext || !userContext.token) {
      console.log('No user context available for sync');
      return;
    }

    // Get the last sync timestamp from IndexedDB or use a default
    const lastSync = await getLastSyncTime();
    let syncUrl = `/api/sync/?last_sync=${lastSync.toISOString()}`;

    // Add school_id if available
    if (userContext.schoolId) {
      syncUrl += `&school_id=${userContext.schoolId}`;
    }

    const response = await fetch(syncUrl, {
      headers: {
        'Authorization': `Bearer ${userContext.token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error('Periodic sync failed');
    }

    const syncData = await response.json();

    // Update cached data with new/updated records
    for (const [model, data] of Object.entries(syncData)) {
      if (model === '_meta') continue; // Skip metadata

      if (Array.isArray(data) && data.length > 0) {
        await cacheData(model, data);
        console.log(`Periodic sync: Updated ${data.length} ${model} records`);
      }
    }

    // Store sync metadata
    if (syncData._meta) {
      await setSyncMetadata(syncData._meta);
    }

    // Update last sync time
    await setLastSyncTime(new Date());

    // Notify clients about data updates
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
      client.postMessage({
        type: 'PERIODIC_SYNC_COMPLETE',
        data: Object.keys(syncData).filter(key => key !== '_meta')
      });
    });

  } catch (error) {
    console.log('Periodic sync failed:', error);
  }
}

// IndexedDB Database Management
const DB_NAME = 'ReportCardAppDB';
const DB_VERSION = 3;

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = event => {
      const db = event.target.result;

      // Pending operations store
      if (!db.objectStoreNames.contains('pendingOperations')) {
        const pendingStore = db.createObjectStore('pendingOperations', { keyPath: 'id', autoIncrement: true });
        pendingStore.createIndex('timestamp', 'timestamp', { unique: false });
        pendingStore.createIndex('model', 'model', { unique: false });
      }

      // Cached data stores
      const models = ['schools', 'users', 'classSections', 'subjects', 'gradingScales', 'studentEnrollments', 'gradingPeriods', 'grades', 'attendance'];

      models.forEach(model => {
        if (!db.objectStoreNames.contains(model)) {
          const store = db.createObjectStore(model, { keyPath: 'id' });
          store.createIndex('updated_at', 'updated_at', { unique: false });
          store.createIndex('school_id', 'school_id', { unique: false });
        }
      });

      // Conflict resolution store
      if (!db.objectStoreNames.contains('conflicts')) {
        const conflictStore = db.createObjectStore('conflicts', { keyPath: 'id', autoIncrement: true });
        conflictStore.createIndex('model', 'model', { unique: false });
        conflictStore.createIndex('local_id', 'local_id', { unique: false });
      }

      // Sync metadata store
      if (!db.objectStoreNames.contains('syncMetadata')) {
        db.createObjectStore('syncMetadata');
      }
    };
  });
}

// Pending Operations Management
async function addPendingOperation(operation) {
  const db = await openDB();
  const transaction = db.transaction(['pendingOperations'], 'readwrite');
  const store = transaction.objectStore('pendingOperations');

  const op = {
    ...operation,
    timestamp: Date.now(),
    retryCount: 0
  };

  return new Promise((resolve, reject) => {
    const request = store.add(op);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getPendingOperations() {
  const db = await openDB();
  const transaction = db.transaction(['pendingOperations'], 'readonly');
  const store = transaction.objectStore('pendingOperations');
  const index = store.index('timestamp');

  return new Promise((resolve, reject) => {
    const request = index.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function removePendingOperation(id) {
  const db = await openDB();
  const transaction = db.transaction(['pendingOperations'], 'readwrite');
  const store = transaction.objectStore('pendingOperations');

  return new Promise((resolve, reject) => {
    const request = store.delete(id);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function updatePendingOperation(id, updates) {
  const db = await openDB();
  const transaction = db.transaction(['pendingOperations'], 'readwrite');
  const store = transaction.objectStore('pendingOperations');

  return new Promise((resolve, reject) => {
    const getRequest = store.get(id);
    getRequest.onsuccess = () => {
      const op = getRequest.result;
      if (op) {
        Object.assign(op, updates);
        const putRequest = store.put(op);
        putRequest.onsuccess = () => resolve();
        putRequest.onerror = () => reject(putRequest.error);
      } else {
        reject(new Error('Operation not found'));
      }
    };
    getRequest.onerror = () => reject(getRequest.error);
  });
}

// Cached Data Management
async function cacheData(model, data) {
  const db = await openDB();
  const transaction = db.transaction([model], 'readwrite');
  const store = transaction.objectStore(model);

  return Promise.all(data.map(item =>
    new Promise((resolve, reject) => {
      const request = store.put(item);
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    })
  ));
}

async function getCachedData(model, schoolId = null) {
  const db = await openDB();
  const transaction = db.transaction([model], 'readonly');
  const store = transaction.objectStore(model);

  return new Promise((resolve, reject) => {
    let request;
    if (schoolId !== null) {
      const index = store.index('school_id');
      request = index.getAll(schoolId);
    } else {
      request = store.getAll();
    }

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getCachedItem(model, id) {
  const db = await openDB();
  const transaction = db.transaction([model], 'readonly');
  const store = transaction.objectStore(model);

  return new Promise((resolve, reject) => {
    const request = store.get(id);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Conflict Detection and Resolution
async function detectConflicts(serverData, model) {
  const conflicts = [];
  const cachedData = await getCachedData(model);

  for (const serverItem of serverData) {
    const cachedItem = cachedData.find(item => item.id === serverItem.id);
    if (cachedItem && cachedItem.updated_at > serverItem.updated_at) {
      conflicts.push({
        model,
        id: serverItem.id,
        server: serverItem,
        local: cachedItem
      });
    }
  }

  return conflicts;
}

async function addConflict(conflict) {
  const db = await openDB();
  const transaction = db.transaction(['conflicts'], 'readwrite');
  const store = transaction.objectStore('conflicts');

  return new Promise((resolve, reject) => {
    const request = store.add(conflict);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getConflicts() {
  const db = await openDB();
  const transaction = db.transaction(['conflicts'], 'readonly');
  const store = transaction.objectStore('conflicts');

  return new Promise((resolve, reject) => {
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Sync timestamp management
async function getLastSyncTime() {
  const db = await openDB();
  const transaction = db.transaction(['syncMetadata'], 'readonly');

  return new Promise((resolve, reject) => {
    const store = transaction.objectStore('syncMetadata');
    const request = store.get('lastSyncTime');

    request.onsuccess = () => {
      if (request.result) {
        resolve(new Date(request.result));
      } else {
        // Default to 24 hours ago if no last sync time
        resolve(new Date(Date.now() - 24 * 60 * 60 * 1000));
      }
    };
    request.onerror = () => reject(request.error);
  });
}

async function setLastSyncTime(timestamp) {
  const db = await openDB();
  const transaction = db.transaction(['syncMetadata'], 'readwrite');

  return new Promise((resolve, reject) => {
    const store = transaction.objectStore('syncMetadata');
    const request = store.put(timestamp.toISOString(), 'lastSyncTime');

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// Utility function to determine model from API URL
function getModelFromUrl(pathname) {
  const modelMap = {
    '/api/schools/': 'schools',
    '/api/users/': 'users',
    '/api/class-sections/': 'classSections',
    '/api/subjects/': 'subjects',
    '/api/grading-scales/': 'gradingScales',
    '/api/student-enrollments/': 'studentEnrollments',
    '/api/grading-periods/': 'gradingPeriods',
    '/api/grades/': 'grades',
    '/api/attendance/': 'attendance'
  };

  for (const [path, model] of Object.entries(modelMap)) {
    if (pathname.startsWith(path)) {
      return model;
    }
  }
  return null;
}

// User context management
async function storeUserContext(userData) {
  const db = await openDB();
  const transaction = db.transaction(['syncMetadata'], 'readwrite');

  return new Promise((resolve, reject) => {
    const store = transaction.objectStore('syncMetadata');
    const request = store.put(userData, 'userContext');

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function getStoredUserContext() {
  const db = await openDB();
  const transaction = db.transaction(['syncMetadata'], 'readonly');

  return new Promise((resolve, reject) => {
    const store = transaction.objectStore('syncMetadata');
    const request = store.get('userContext');

    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error);
  });
}

// Sync metadata management
async function setSyncMetadata(metadata) {
  const db = await openDB();
  const transaction = db.transaction(['syncMetadata'], 'readwrite');

  return new Promise((resolve, reject) => {
    const store = transaction.objectStore('syncMetadata');
    const request = store.put(metadata, 'syncMeta');

    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function getSyncMetadata() {
  const db = await openDB();
  const transaction = db.transaction(['syncMetadata'], 'readonly');

  return new Promise((resolve, reject) => {
    const store = transaction.objectStore('syncMetadata');
    const request = store.get('syncMeta');

    request.onsuccess = () => resolve(request.result || {});
    request.onerror = () => reject(request.error);
  });
}

// Message handling from client
self.addEventListener('message', event => {
  const { type, data, port } = event;

  switch (type) {
    case 'ADD_PENDING_OPERATION':
      addPendingOperation(data.operation)
        .then(() => port.postMessage({ success: true }))
        .catch(error => port.postMessage({ success: false, error: error.message }));
      break;

    case 'GET_CACHED_DATA':
      getCachedData(data.model, data.schoolId)
        .then(cachedData => port.postMessage(cachedData))
        .catch(error => port.postMessage(null));
      break;

    case 'GET_CONFLICTS':
      getConflicts()
        .then(conflicts => port.postMessage(conflicts))
        .catch(error => port.postMessage([]));
      break;

    case 'RESOLVE_CONFLICT':
      resolveConflict(data.conflictId, data.resolution)
        .then(() => port.postMessage({ success: true }))
        .catch(error => port.postMessage({ success: false, error: error.message }));
      break;

    case 'SYNC_NOW':
      doBackgroundSync()
        .then(() => port.postMessage({ success: true }))
        .catch(error => port.postMessage({ success: false, error: error.message }));
      break;

    case 'STORE_USER_CONTEXT':
      storeUserContext(data)
        .then(() => port.postMessage({ success: true }))
        .catch(error => port.postMessage({ success: false, error: error.message }));
      break;

    case 'GET_USER_CONTEXT':
      getStoredUserContext()
        .then(context => port.postMessage(context))
        .catch(error => port.postMessage(null));
      break;

    case 'CACHE_API_RESPONSE':
      // Cache API response data in IndexedDB
      if (data.model && data.data) {
        cacheData(data.model, Array.isArray(data.data) ? data.data : [data.data])
          .then(() => port.postMessage({ success: true }))
          .catch(error => port.postMessage({ success: false, error: error.message }));
      } else {
        port.postMessage({ success: false, error: 'Invalid data format' });
      }
      break;

    default:
      port.postMessage({ error: 'Unknown message type' });
  }
});

async function resolveConflict(conflictId, resolution) {
  const db = await openDB();
  const transaction = db.transaction(['conflicts'], 'readwrite');
  const store = transaction.objectStore('conflicts');

  return new Promise((resolve, reject) => {
    const request = store.delete(conflictId);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}
