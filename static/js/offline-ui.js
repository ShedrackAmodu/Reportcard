// Offline UI Components - Visual indicators and controls for offline functionality
class OfflineUIManager {
  constructor() {
    this.setupOfflineIndicator();
    this.setupSyncButton();
    this.setupOfflineNotifications();
    this.setupFormHandlers();
    this.setupEventListeners();
  }

  setupOfflineIndicator() {
    // Create offline status indicator
    const indicator = document.createElement('div');
    indicator.id = 'offlineStatusIndicator';
    indicator.className = 'offline-status-indicator online';
    indicator.innerHTML = `
      <div class="indicator-content">
        <i class="bi bi-wifi"></i>
        <span class="status-text">Online</span>
      </div>
    `;
    document.body.appendChild(indicator);

    // Listen for network status changes
    window.addEventListener('offline:online-status-changed', (e) => {
      this.updateOfflineIndicator(e.detail.isOnline);
    });
  }

  updateOfflineIndicator(isOnline) {
    const indicator = document.getElementById('offlineStatusIndicator');
    if (!indicator) return;

    if (isOnline) {
      indicator.classList.remove('offline', 'syncing');
      indicator.classList.add('online');
      indicator.innerHTML = `
        <div class="indicator-content">
          <i class="bi bi-wifi"></i>
          <span class="status-text">Online</span>
        </div>
      `;
    } else {
      indicator.classList.remove('online', 'syncing');
      indicator.classList.add('offline');
      indicator.innerHTML = `
        <div class="indicator-content">
          <i class="bi bi-wifi-off"></i>
          <span class="status-text">Offline</span>
        </div>
      `;
    }
  }

  setupSyncButton() {
    // Create manual sync button
    const button = document.createElement('button');
    button.id = 'offlineSyncButton';
    button.className = 'btn btn-outline-primary offline-sync-btn';
    button.title = 'Sync offline changes';
    button.innerHTML = `
      <i class="bi bi-arrow-repeat"></i>
      <span>Sync Now</span>
    `;
    button.onclick = async () => await this.manualSync();
    document.body.appendChild(button);

    this.updateSyncButtonVisibility();

    // Listen for network status changes
    window.addEventListener('offline:online-status-changed', () => {
      this.updateSyncButtonVisibility();
    });

    // Listen for sync events
    window.addEventListener('offline:sync-started', () => {
      button.disabled = true;
      button.classList.add('syncing');
    });

    window.addEventListener('offline:sync-completed', () => {
      button.disabled = false;
      button.classList.remove('syncing');
    });
  }

  async updateSyncButtonVisibility() {
    const button = document.getElementById('offlineSyncButton');
    if (!button) return;

    const stats = await offlineDB.getStats();
    const hasPending = stats.pendingOperations > 0 || stats.offlineChanges > 0;

    if (hasPending) {
      button.style.display = 'flex';
      button.setAttribute('data-badge', stats.pendingOperations + stats.offlineChanges);
    } else {
      button.style.display = 'none';
    }
  }

  async manualSync() {
    const button = document.getElementById('offlineSyncButton');
    if (button) {
      button.disabled = true;
      button.classList.add('syncing');
    }

    try {
      await syncManager.performSync();
      this.showSyncNotification('Sync completed successfully', 'success');
      await this.updateSyncButtonVisibility();
    } catch (error) {
      this.showSyncNotification(`Sync failed: ${error.message}`, 'danger');
    } finally {
      if (button) {
        button.disabled = false;
        button.classList.remove('syncing');
      }
    }
  }

  setupOfflineNotifications() {
    // Listen for sync events
    window.addEventListener('offline:sync-started', () => {
      this.showNotification('Syncing offline changes...', 'info', 0);
    });

    window.addEventListener('offline:sync-completed', (e) => {
      const { synced, failed } = e.detail;
      if (failed === 0) {
        this.showSyncNotification(
          `Successfully synced ${synced} items`,
          'success',
          3000
        );
      } else {
        this.showSyncNotification(
          `Synced ${synced} items, ${failed} failed`,
          'warning',
          5000
        );
      }
    });

    window.addEventListener('offline:sync-failed', (e) => {
      this.showSyncNotification(
        `Sync failed: ${e.detail.error}`,
        'danger',
        5000
      );
    });

    window.addEventListener('offline:form-submitted-offline', (e) => {
      this.showNotification(
        'Changes saved offline. They will sync when you\'re back online.',
        'info',
        3000
      );
    });
  }

  showSyncNotification(message, type = 'info', duration = 3000) {
    this.showNotification(message, type, duration);
  }

  showNotification(message, type = 'info', duration = 3000) {
    const container = document.getElementById('offlineNotificationsContainer') || this.createNotificationContainer();
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} offline-notification fade show`;
    notification.innerHTML = `
      <div class="notification-content">
        <i class="bi bi-info-circle"></i>
        <span>${message}</span>
      </div>
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    container.appendChild(notification);

    if (duration > 0) {
      setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
      }, duration);
    }
  }

  createNotificationContainer() {
    const container = document.createElement('div');
    container.id = 'offlineNotificationsContainer';
    container.className = 'offline-notifications-container';
    document.body.appendChild(container);
    return container;
  }

  setupFormHandlers() {
    // Intercept all form submissions
    document.addEventListener('submit', async (e) => {
      const form = e.target;
      
      // Skip if form is explicitly marked to not handle offline
      if (form.dataset.offlineDisabled === 'true') {
        return;
      }

      // Check if offline
      if (!syncManager.isOnline) {
        e.preventDefault();

        const model = form.dataset.model || this.guessModelFromForm(form);
        const formName = form.name || form.id || 'form';

        // Show confirmation
        if (confirm('You are offline. Save changes locally?\n\nThey will sync when you\'re back online.')) {
          const objectId = await syncManager.submitFormOffline(form, model);
          
          // Show success message
          this.showNotification(
            'Changes saved offline and will be synced automatically.',
            'success',
            3000
          );

          // Reset form if needed
          if (form.dataset.resetAfterSubmit === 'true') {
            form.reset();
          }

          // Redirect if needed
          if (form.dataset.redirectAfter) {
            setTimeout(() => {
              window.location.href = form.dataset.redirectAfter;
            }, 1500);
          }
        }
      }
    });
  }

  guessModelFromForm(form) {
    // Try to get model from form classes
    const classes = form.className || '';
    const match = classes.match(/form-(\w+)/);
    if (match) return match[1];

    // Try from form action
    const action = form.action || '';
    const apiMatch = action.match(/\/api\/(\w+)\//);
    if (apiMatch) return apiMatch[1];

    // Try from data attribute
    return form.dataset.model || 'unknown';
  }

  setupEventListeners() {
    // Listen for offline changes
    window.addEventListener('offline:online-status-changed', (e) => {
      this.updateUIForOnlineStatus(e.detail.isOnline);
    });
  }

  updateUIForOnlineStatus(isOnline) {
    // Disable/enable forms and buttons based on online status
    const forms = document.querySelectorAll('form:not([data-offline-disabled="true"])');
    forms.forEach(form => {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = false; // Can still submit offline
        if (!isOnline) {
          submitBtn.classList.add('offline-mode');
        } else {
          submitBtn.classList.remove('offline-mode');
        }
      }
    });
  }

  // Show offline data information
  async showOfflineDataInfo() {
    const stats = await offlineDB.getStats();
    const info = `
      <h5>Offline Status</h5>
      <ul>
        <li>Pending Operations: ${stats.pendingOperations}</li>
        <li>Offline Changes: ${stats.offlineChanges}</li>
        <li>Conflicts: ${stats.conflicts}</li>
        <li>Last Sync: ${stats.lastSyncTime ? stats.lastSyncTime.toLocaleString() : 'Never'}</li>
      </ul>
    `;
    this.showNotification(info, 'info', 0);
  }

  // Show conflict resolution dialog
  async showConflictResolutionDialog(conflict) {
    return new Promise((resolve) => {
      const modal = document.createElement('div');
      modal.className = 'modal fade show';
      modal.style.display = 'block';
      modal.innerHTML = `
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Resolve Conflict</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <p>A conflict was detected for <strong>${conflict.model} #${conflict.object_id}</strong></p>
              <div class="row">
                <div class="col-md-6">
                  <h6>Your Changes</h6>
                  <pre><code>${JSON.stringify(conflict.local, null, 2)}</code></pre>
                </div>
                <div class="col-md-6">
                  <h6>Server Version</h6>
                  <pre><code>${JSON.stringify(conflict.server, null, 2)}</code></pre>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" onclick="this.parentElement.parentElement.parentElement.remove()">Cancel</button>
              <button type="button" class="btn btn-primary" data-action="keep-server">Use Server Version</button>
              <button type="button" class="btn btn-success" data-action="keep-local">Keep My Changes</button>
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      const buttons = modal.querySelectorAll('[data-action]');
      buttons.forEach(btn => {
        btn.onclick = async () => {
          const action = btn.dataset.action;
          modal.remove();
          resolve(action);
        };
      });
    });
  }
}

// Global instance
const offlineUI = new OfflineUIManager();
