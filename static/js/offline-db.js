// Offline Database Manager - Comprehensive IndexedDB storage for offline-first support
class OfflineDatabase {
  constructor() {
    this.DB_NAME = 'ReportCardAppDB';
    this.DB_VERSION = 4;
    this.db = null;
    this.isReady = false;
    this.initPromise = this.init();
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.DB_NAME, this.DB_VERSION);

      request.onerror = () => {
        console.error('Failed to open IndexedDB:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        this.isReady = true;
        console.log('IndexedDB initialized successfully');
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        console.log('Upgrading IndexedDB schema...');

        // Define all object stores
        const stores = {
          schools: { keyPath: 'id', indexes: ['name'] },
          users: { keyPath: 'id', indexes: ['username', 'email', 'school_id'] },
          classSections: { keyPath: 'id', indexes: ['school_id', 'teacher_id', 'name'] },
          subjects: { keyPath: 'id', indexes: ['school_id', 'code'] },
          gradingScales: { keyPath: 'id', indexes: ['school_id', 'name'] },
          gradingPeriods: { keyPath: 'id', indexes: ['school_id', 'name'] },
          studentEnrollments: { keyPath: 'id', indexes: ['student_id', 'class_section_id', 'school_id'] },
          grades: { keyPath: 'id', indexes: ['student_id', 'subject_id', 'grading_period_id', 'school_id'] },
          attendance: { keyPath: 'id', indexes: ['student_id', 'class_section_id', 'date', 'school_id'] },
          reportCards: { keyPath: 'id', indexes: ['student_id', 'grading_period_id', 'school_id'] },
          reportTemplates: { keyPath: 'id', indexes: ['school_id', 'name'] },
          pendingOperations: { keyPath: 'id', autoIncrement: true, indexes: ['timestamp', 'model', 'status'] },
          syncConflicts: { keyPath: 'id', autoIncrement: true, indexes: ['model', 'object_id', 'timestamp'] },
          syncMetadata: { keyPath: 'key' },
          offlineChanges: { keyPath: 'id', autoIncrement: true, indexes: ['model', 'object_id', 'timestamp'] }
        };

        // Create or update object stores
        for (const [storeName, config] of Object.entries(stores)) {
          if (!db.objectStoreNames.contains(storeName)) {
            const store = db.createObjectStore(storeName, {
              keyPath: config.keyPath,
              autoIncrement: config.autoIncrement
            });

            // Create indexes
            if (config.indexes) {
              config.indexes.forEach(indexName => {
                store.createIndex(indexName, indexName, { unique: false });
              });
            }
          }
        }

        console.log('IndexedDB schema upgraded successfully');
      };
    });
  }

  async ready() {
    return this.initPromise;
  }

  // Generic data operations
  async add(storeName, data) {
    await this.ready();
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.add(data);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async put(storeName, data) {
    await this.ready();
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.put(data);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async get(storeName, key) {
    await this.ready();
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      const request = store.get(key);

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getAll(storeName, query = null) {
    await this.ready();
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readonly');
      const store = transaction.objectStore(storeName);
      
      let request;
      if (query && query.index && query.value) {
        const index = store.index(query.index);
        request = index.getAll(query.value);
      } else {
        request = store.getAll();
      }

      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  async delete(storeName, key) {
    await this.ready();
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.delete(key);

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async clear(storeName) {
    await this.ready();
    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([storeName], 'readwrite');
      const store = transaction.objectStore(storeName);
      const request = store.clear();

      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  // Batch operations
  async putBatch(storeName, items) {
    await this.ready();
    const transaction = this.db.transaction([storeName], 'readwrite');
    const store = transaction.objectStore(storeName);
    
    return new Promise((resolve, reject) => {
      const promises = items.map(item => 
        new Promise((res, rej) => {
          const request = store.put(item);
          request.onsuccess = () => res();
          request.onerror = () => rej(request.error);
        })
      );

      Promise.all(promises)
        .then(() => resolve())
        .catch(reject);
    });
  }

  // Pending operations management
  async addPendingOperation(operation) {
    const op = {
      ...operation,
      timestamp: Date.now(),
      status: 'pending',
      retryCount: 0
    };
    return this.add('pendingOperations', op);
  }

  async getPendingOperations(status = null) {
    if (status) {
      return this.getAll('pendingOperations', { index: 'status', value: status });
    }
    return this.getAll('pendingOperations');
  }

  async removePendingOperation(id) {
    return this.delete('pendingOperations', id);
  }

  async updatePendingOperation(id, updates) {
    const op = await this.get('pendingOperations', id);
    if (op) {
      Object.assign(op, updates, { id });
      return this.put('pendingOperations', op);
    }
  }

  // Conflict management
  async addConflict(conflict) {
    const data = {
      ...conflict,
      timestamp: Date.now()
    };
    return this.add('syncConflicts', data);
  }

  async getConflicts(model = null) {
    if (model) {
      return this.getAll('syncConflicts', { index: 'model', value: model });
    }
    return this.getAll('syncConflicts');
  }

  async removeConflict(id) {
    return this.delete('syncConflicts', id);
  }

  // Offline changes tracking
  async trackOfflineChange(model, objectId, action, data) {
    const change = {
      model,
      object_id: objectId,
      action, // 'create', 'update', 'delete'
      data,
      timestamp: Date.now()
    };
    return this.add('offlineChanges', change);
  }

  async getOfflineChanges(model = null) {
    if (model) {
      return this.getAll('offlineChanges', { index: 'model', value: model });
    }
    return this.getAll('offlineChanges');
  }

  async clearOfflineChanges() {
    return this.clear('offlineChanges');
  }

  // Metadata operations
  async setMetadata(key, value) {
    const data = { key, value, timestamp: Date.now() };
    return this.put('syncMetadata', data);
  }

  async getMetadata(key) {
    const data = await this.get('syncMetadata', key);
    return data ? data.value : null;
  }

  async getAllMetadata() {
    return this.getAll('syncMetadata');
  }

  // User context
  async setUserContext(context) {
    return this.setMetadata('userContext', context);
  }

  async getUserContext() {
    return this.getMetadata('userContext');
  }

  // Sync timestamps
  async setLastSyncTime(timestamp) {
    return this.setMetadata('lastSyncTime', timestamp.toISOString());
  }

  async getLastSyncTime() {
    const timestamp = await this.getMetadata('lastSyncTime');
    if (timestamp) {
      return new Date(timestamp);
    }
    // Default to 24 hours ago
    return new Date(Date.now() - 24 * 60 * 60 * 1000);
  }

  async setLastFullSyncTime(timestamp) {
    return this.setMetadata('lastFullSyncTime', timestamp.toISOString());
  }

  async getLastFullSyncTime() {
    const timestamp = await this.getMetadata('lastFullSyncTime');
    if (timestamp) {
      return new Date(timestamp);
    }
    return new Date(0); // Epoch time if never synced
  }

  // Sync state
  async setSyncState(state) {
    return this.setMetadata('syncState', state);
  }

  async getSyncState() {
    return this.getMetadata('syncState');
  }

  // Statistics
  async getStats() {
    const pendingOps = await this.getPendingOperations();
    const conflicts = await this.getConflicts();
    const changes = await this.getOfflineChanges();
    
    return {
      pendingOperations: pendingOps.length,
      conflicts: conflicts.length,
      offlineChanges: changes.length,
      lastSyncTime: await this.getLastSyncTime(),
      isReady: this.isReady
    };
  }

  // Clear all data - used for logout
  async clearAllData() {
    await this.ready();
    const storeNames = [
      'schools', 'users', 'classSections', 'subjects', 'gradingScales',
      'gradingPeriods', 'studentEnrollments', 'grades', 'attendance',
      'reportCards', 'reportTemplates', 'pendingOperations', 'syncConflicts',
      'syncMetadata', 'offlineChanges'
    ];
    
    for (const storeName of storeNames) {
      try {
        await this.clear(storeName);
      } catch (error) {
        console.warn(`Failed to clear ${storeName}:`, error);
      }
    }
    
    console.log('All offline data cleared');
  }
}

// Global instance
const offlineDB = new OfflineDatabase();
