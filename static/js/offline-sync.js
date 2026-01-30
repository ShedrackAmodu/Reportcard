// Offline Sync Manager - Handles synchronization and conflict resolution
class OfflineSyncManager {
  constructor() {
    this.syncInProgress = false;
    this.syncInterval = null;
    this.conflictHandlers = {};
    this.isOnline = navigator.onLine;
    this.setupNetworkDetection();
  }

  setupNetworkDetection() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.dispatchEvent('online-status-changed', { isOnline: true });
      this.triggerSync();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.dispatchEvent('online-status-changed', { isOnline: false });
    });
  }

  async triggerSync(force = false) {
    if (this.syncInProgress && !force) {
      console.log('Sync already in progress');
      return;
    }

    if (!this.isOnline && !force) {
      console.log('Offline - skipping sync');
      return;
    }

    await this.performSync();
  }

  async performSync() {
    this.syncInProgress = true;
    this.dispatchEvent('sync-started', {});

    try {
      // Get user context
      const userContext = await offlineDB.getUserContext();
      if (!userContext || !userContext.token) {
        throw new Error('No authentication token available');
      }

      // Get pending operations
      const pendingOps = await offlineDB.getPendingOperations('pending');
      
      if (pendingOps.length === 0) {
        console.log('No pending operations to sync');
        this.dispatchEvent('sync-completed', { synced: 0, failed: 0 });
        this.syncInProgress = false;
        return;
      }

      let synced = 0;
      let failed = 0;

      // Process each pending operation
      for (const op of pendingOps) {
        try {
          const success = await this.executePendingOperation(op, userContext);
          if (success) {
            synced++;
            await offlineDB.removePendingOperation(op.id);
          } else {
            failed++;
            await offlineDB.updatePendingOperation(op.id, {
              retryCount: (op.retryCount || 0) + 1,
              lastError: new Date().toISOString()
            });
          }
        } catch (error) {
          failed++;
          console.error('Error syncing operation:', error);
          await offlineDB.updatePendingOperation(op.id, {
            retryCount: (op.retryCount || 0) + 1,
            lastError: error.message
          });
        }
      }

      // Update last sync time
      await offlineDB.setLastSyncTime(new Date());

      // Check for conflicts
      await this.checkAndResolveConflicts();

      this.dispatchEvent('sync-completed', { synced, failed });
    } catch (error) {
      console.error('Sync failed:', error);
      this.dispatchEvent('sync-failed', { error: error.message });
    } finally {
      this.syncInProgress = false;
    }
  }

  async executePendingOperation(operation, userContext) {
    const { url, method, body, type } = operation;

    try {
      const options = {
        method: method || 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userContext.token}`,
          'X-CSRFToken': this.getCsrfToken()
        }
      };

      if (body) {
        options.body = typeof body === 'string' ? body : JSON.stringify(body);
      }

      const response = await fetch(url, options);

      if (response.ok) {
        // Cache the response if it's API data
        if (url.includes('/api/')) {
          try {
            const data = await response.json();
            await this.cacheResponseData(operation.model, data);
          } catch (e) {
            // Ignore parsing errors
          }
        }
        return true;
      } else if (response.status === 409) {
        // Conflict detected
        const conflict = await response.json();
        await offlineDB.addConflict({
          model: operation.model,
          object_id: operation.objectId,
          server: conflict.server,
          local: JSON.parse(body)
        });
        return false;
      } else {
        return false;
      }
    } catch (error) {
      console.error('Error executing operation:', error);
      return false;
    }
  }

  async cacheResponseData(model, data) {
    if (Array.isArray(data)) {
      await offlineDB.putBatch(model, data);
    } else if (data && data.results && Array.isArray(data.results)) {
      await offlineDB.putBatch(model, data.results);
    } else if (data && data.id) {
      await offlineDB.put(model, data);
    }
  }

  async checkAndResolveConflicts() {
    const conflicts = await offlineDB.getConflicts();
    
    for (const conflict of conflicts) {
      const handler = this.conflictHandlers[conflict.model];
      if (handler) {
        try {
          const resolution = await handler(conflict);
          if (resolution === 'keep-local') {
            // Update server with local data
            await this.syncLocalToServer(conflict);
          } else if (resolution === 'keep-server') {
            // Update local with server data
            await offlineDB.put(conflict.model, conflict.server);
          } else if (resolution === 'merge') {
            // Custom merge logic
            const merged = this.mergeConflict(conflict);
            await offlineDB.put(conflict.model, merged);
            await this.syncLocalToServer(conflict, merged);
          }
          await offlineDB.removeConflict(conflict.id);
        } catch (error) {
          console.error('Error resolving conflict:', error);
        }
      }
    }
  }

  registerConflictHandler(model, handler) {
    this.conflictHandlers[model] = handler;
  }

  mergeConflict(conflict) {
    // Default merge strategy: prefer local changes but keep server timestamps
    const merged = { ...conflict.server, ...conflict.local };
    merged.merged_at = new Date().toISOString();
    merged.merged_from_conflict = true;
    return merged;
  }

  async syncLocalToServer(conflict, data) {
    const userContext = await offlineDB.getUserContext();
    if (!userContext) return;

    const response = await fetch(
      `/api/${conflict.model}/${conflict.object_id}/`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userContext.token}`,
          'X-CSRFToken': this.getCsrfToken()
        },
        body: JSON.stringify(data || conflict.local)
      }
    );

    return response.ok;
  }

  // Form submission handling
  async submitFormOffline(form, model) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Track as offline change
    const isNew = !data.id;
    const objectId = data.id || `temp_${Date.now()}`;
    
    await offlineDB.trackOfflineChange(
      model,
      objectId,
      isNew ? 'create' : 'update',
      data
    );

    // Add as pending operation
    await offlineDB.addPendingOperation({
      type: 'form_submission',
      model,
      objectId,
      url: form.action,
      method: form.method || 'POST',
      body: JSON.stringify(data)
    });

    // Update UI to reflect offline state
    this.dispatchEvent('form-submitted-offline', {
      model,
      objectId,
      data
    });

    return objectId;
  }

  async bulkUploadData(model, items) {
    const userContext = await offlineDB.getUserContext();
    if (!userContext) throw new Error('Not authenticated');

    const operations = items.map(item => ({
      type: 'bulk_upload',
      model,
      objectId: item.id,
      url: `/api/${model}/bulk/`,
      method: 'POST',
      body: JSON.stringify({ items })
    }));

    for (const op of operations) {
      await offlineDB.addPendingOperation(op);
    }

    return operations.length;
  }

  // Data loading for offline view
  async loadOfflineData(model, filters = {}) {
    try {
      const data = await offlineDB.getAll(model);
      
      // Apply filters
      if (filters && Object.keys(filters).length > 0) {
        return data.filter(item => {
          return Object.entries(filters).every(([key, value]) => {
            return item[key] === value;
          });
        });
      }

      return data;
    } catch (error) {
      console.error(`Error loading offline data for ${model}:`, error);
      return [];
    }
  }

  // Get last sync info
  async getSyncInfo() {
    return offlineDB.getStats();
  }

  // Event system
  dispatchEvent(eventName, detail) {
    const event = new CustomEvent(`offline:${eventName}`, { detail });
    window.dispatchEvent(event);
  }

  // Utility
  getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Start periodic sync
  startPeriodicSync(intervalMs = 30000) {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
    }

    this.syncInterval = setInterval(() => {
      if (this.isOnline) {
        this.performSync();
      }
    }, intervalMs);
  }

  // Stop periodic sync
  stopPeriodicSync() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  // Clear all offline data
  async clearAllOfflineData() {
    const stores = [
      'schools', 'users', 'classSections', 'subjects', 'gradingScales',
      'gradingPeriods', 'studentEnrollments', 'grades', 'attendance',
      'reportCards', 'reportTemplates', 'pendingOperations', 'offlineChanges'
    ];

    for (const store of stores) {
      await offlineDB.clear(store);
    }

    return true;
  }
}

// Global instance
const syncManager = new OfflineSyncManager();
