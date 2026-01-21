// SchoolSync PWA Client-side JavaScript
class SchoolSyncPWA {
    constructor() {
        this.isOnline = navigator.onLine;
        this.syncInProgress = false;
        this.pullToRefreshEnabled = false;
        this.touchStartY = 0;

        this.init();
    }

    init() {
        this.setupNetworkDetection();
        this.setupSyncStatus();
        this.setupPullToRefresh();
        this.setupSwipeGestures();
        this.setupOfflineForms();
        this.loadCachedData();
        this.setupPeriodicSync();

        // Check for conflicts on load
        this.checkForConflicts();
    }

    setupNetworkDetection() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateSyncStatus('online');
            this.triggerSync();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateSyncStatus('offline');
        });

        // Initial status
        this.updateSyncStatus(this.isOnline ? 'online' : 'offline');
    }

    setupSyncStatus() {
        // Create sync status indicator
        const statusEl = document.createElement('div');
        statusEl.id = 'syncStatusIndicator';
        statusEl.className = 'sync-status';
        document.body.appendChild(statusEl);

        // Create network quality indicator
        const networkEl = document.createElement('div');
        networkEl.id = 'networkQualityIndicator';
        networkEl.className = 'network-quality';
        document.body.appendChild(networkEl);

        // Add manual sync button
        const syncBtn = document.createElement('button');
        syncBtn.id = 'manualSyncBtn';
        syncBtn.className = 'btn btn-outline-primary position-fixed';
        syncBtn.style.cssText = 'bottom: 20px; right: 20px; z-index: 999; display: none;';
        syncBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Sync Now';
        syncBtn.onclick = () => this.manualSync();
        document.body.appendChild(syncBtn);
    }

    updateSyncStatus(status) {
        const statusEl = document.getElementById('syncStatusIndicator');
        if (!statusEl) return;

        statusEl.className = 'sync-status';

        switch(status) {
            case 'online':
                statusEl.classList.add('online');
                statusEl.textContent = '● Online';
                document.getElementById('manualSyncBtn').style.display = 'none';
                break;
            case 'offline':
                statusEl.classList.add('offline');
                statusEl.textContent = '● Offline';
                document.getElementById('manualSyncBtn').style.display = 'block';
                break;
            case 'syncing':
                statusEl.classList.add('syncing');
                statusEl.textContent = '● Syncing...';
                break;
            case 'error':
                statusEl.classList.add('error');
                statusEl.textContent = '● Sync Error';
                document.getElementById('manualSyncBtn').style.display = 'block';
                break;
        }
    }

    async manualSync() {
        if (this.syncInProgress) return;

        this.updateSyncStatus('syncing');
        this.syncInProgress = true;

        try {
            await this.performSync();
            this.updateSyncStatus('online');
        } catch (error) {
            console.error('Manual sync failed:', error);
            this.updateSyncStatus('error');
        } finally {
            this.syncInProgress = false;
        }
    }

    async performSync() {
        // Get pending operations from service worker
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
                type: 'SYNC_NOW'
            });
        }

        // Trigger background sync
        if ('serviceWorker' in navigator) {
            const registration = await navigator.serviceWorker.ready;
            if ('sync' in registration) {
                await registration.sync.register('background-sync');
            }
        }
    }

    setupPullToRefresh() {
        let startY = 0;
        let isPulling = false;

        document.addEventListener('touchstart', (e) => {
            if (window.scrollY === 0) {
                startY = e.touches[0].clientY;
                isPulling = true;
            }
        });

        document.addEventListener('touchmove', (e) => {
            if (!isPulling || !this.isOnline) return;

            const currentY = e.touches[0].clientY;
            const pullDistance = currentY - startY;

            if (pullDistance > 50) {
                e.preventDefault();
                this.showPullIndicator();
            }
        });

        document.addEventListener('touchend', async (e) => {
            if (!isPulling) return;

            const endY = e.changedTouches[0].clientY;
            const pullDistance = endY - startY;

            this.hidePullIndicator();

            if (pullDistance > 100 && this.isOnline) {
                await this.manualSync();
            }

            isPulling = false;
        });
    }

    showPullIndicator() {
        let indicator = document.getElementById('pullIndicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'pullIndicator';
            indicator.className = 'pull-to-refresh';
            indicator.textContent = 'Release to sync';
            document.body.appendChild(indicator);
        }
        indicator.classList.add('show');
    }

    hidePullIndicator() {
        const indicator = document.getElementById('pullIndicator');
        if (indicator) {
            indicator.classList.remove('show');
        }
    }

    setupSwipeGestures() {
        let startX = 0;
        let startY = 0;

        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });

        document.addEventListener('touchend', (e) => {
            if (!startX || !startY) return;

            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;

            const deltaX = endX - startX;
            const deltaY = endY - startY;

            // Only handle horizontal swipes
            if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
                if (deltaX > 0) {
                    this.handleSwipe('right');
                } else {
                    this.handleSwipe('left');
                }
            }

            startX = startY = 0;
        });
    }

    handleSwipe(direction) {
        // Show swipe hint for first-time users
        if (!localStorage.getItem('swipeHintShown')) {
            this.showSwipeHint();
            localStorage.setItem('swipeHintShown', 'true');
        }

        // Handle navigation or other swipe actions
        const currentPath = window.location.pathname;

        if (direction === 'left' && currentPath.includes('/list')) {
            // Swipe left on list pages could go to next page
            this.navigateList('next');
        } else if (direction === 'right' && currentPath.includes('/list')) {
            // Swipe right on list pages could go to previous page
            this.navigateList('prev');
        }
    }

    showSwipeHint() {
        const hint = document.createElement('div');
        hint.className = 'swipe-hint';
        hint.textContent = 'Swipe left/right to navigate';
        document.body.appendChild(hint);

        setTimeout(() => {
            hint.classList.add('show');
            setTimeout(() => {
                hint.remove();
            }, 3000);
        }, 1000);
    }

    navigateList(direction) {
        // Simple pagination navigation
        const nextBtn = document.querySelector('.pagination .next');
        const prevBtn = document.querySelector('.pagination .prev');

        if (direction === 'next' && nextBtn) {
            nextBtn.click();
        } else if (direction === 'prev' && prevBtn) {
            prevBtn.click();
        }
    }

    setupOfflineForms() {
        // Intercept form submissions when offline
        document.addEventListener('submit', async (e) => {
            const form = e.target;
            if (!this.isOnline && form.dataset.offline !== 'false') {
                e.preventDefault();
                await this.handleOfflineSubmission(form);
            }
        });
    }

    async handleOfflineSubmission(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Add to pending operations
        const operation = {
            type: 'form_submission',
            url: form.action,
            method: form.method || 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: new URLSearchParams(data).toString(),
            timestamp: Date.now()
        };

        try {
            await this.addPendingOperation(operation);
            this.showOfflineNotification('Form saved offline. Will sync when online.');
            form.reset();
        } catch (error) {
            console.error('Failed to save offline:', error);
            this.showOfflineNotification('Failed to save offline. Please try again.', 'error');
        }
    }

    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    async addPendingOperation(operation) {
        // Send to service worker
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
                type: 'ADD_PENDING_OPERATION',
                operation: operation
            });
        }
    }

    showOfflineNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 70px; right: 20px; z-index: 1000; max-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    async loadCachedData() {
        // Load cached data for offline viewing
        const tables = document.querySelectorAll('table[data-model]');
        for (const table of tables) {
            const model = table.dataset.model;
            if (!this.isOnline) {
                await this.loadTableFromCache(table, model);
            }
        }
    }

    async loadTableFromCache(table, model) {
        try {
            const cachedData = await this.getCachedData(model);
            if (cachedData && cachedData.length > 0) {
                this.populateTable(table, cachedData);
                table.classList.add('offline-indicator');
            }
        } catch (error) {
            console.error('Failed to load cached data:', error);
        }
    }

    async getCachedData(model) {
        // Request cached data from service worker
        return new Promise((resolve) => {
            const channel = new MessageChannel();

            channel.port1.onmessage = (event) => {
                resolve(event.data);
            };

            if (navigator.serviceWorker.controller) {
                navigator.serviceWorker.controller.postMessage({
                    type: 'GET_CACHED_DATA',
                    model: model
                }, [channel.port2]);
            } else {
                resolve(null);
            }
        });
    }

    populateTable(table, data) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        tbody.innerHTML = '';

        data.forEach(item => {
            const row = document.createElement('tr');

            // Create cells based on table headers
            const headers = table.querySelectorAll('thead th');
            headers.forEach(header => {
                const cell = document.createElement('td');
                const field = header.dataset.field;
                if (field) {
                    cell.textContent = item[field] || '';
                }
                row.appendChild(cell);
            });

            tbody.appendChild(row);
        });
    }

    async checkForConflicts() {
        // Check for unresolved conflicts
        const conflicts = await this.getConflicts();
        if (conflicts && conflicts.length > 0) {
            this.showConflictModal(conflicts);
        }
    }

    async getConflicts() {
        return new Promise((resolve) => {
            const channel = new MessageChannel();

            channel.port1.onmessage = (event) => {
                resolve(event.data);
            };

            if (navigator.serviceWorker.controller) {
                navigator.serviceWorker.controller.postMessage({
                    type: 'GET_CONFLICTS'
                }, [channel.port2]);
            } else {
                resolve([]);
            }
        });
    }

    showConflictModal(conflicts) {
        const modal = document.createElement('div');
        modal.className = 'conflict-modal';
        modal.innerHTML = `
            <div class="conflict-content">
                <h5>Sync Conflicts Detected</h5>
                <p>Some data was modified both locally and on the server. Please choose how to resolve:</p>

                <div id="conflictList">
                    ${conflicts.map(conflict => `
                        <div class="conflict-item mb-3 p-3 border rounded">
                            <h6>${conflict.model}: ${conflict.id}</h6>
                            <div class="conflict-options">
                                <div class="conflict-option" onclick="pwa.resolveConflict(${conflict.id}, 'server')">
                                    Use Server Version
                                </div>
                                <div class="conflict-option" onclick="pwa.resolveConflict(${conflict.id}, 'local')">
                                    Keep Local Changes
                                </div>
                                <div class="conflict-option" onclick="pwa.resolveConflict(${conflict.id}, 'merge')">
                                    Merge Changes
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>

                <button class="btn btn-secondary" onclick="this.parentElement.parentElement.remove()">Resolve Later</button>
            </div>
        `;
        document.body.appendChild(modal);
    }

    async resolveConflict(conflictId, resolution) {
        try {
            await this.sendMessageToSW({
                type: 'RESOLVE_CONFLICT',
                conflictId: conflictId,
                resolution: resolution
            });

            // Remove the conflict item from UI
            const conflictItem = document.querySelector(`[onclick*="resolveConflict(${conflictId}"]`);
            if (conflictItem) {
                conflictItem.closest('.conflict-item').remove();
            }

            // Close modal if no more conflicts
            const remaining = document.querySelectorAll('.conflict-item');
            if (remaining.length === 0) {
                document.querySelector('.conflict-modal').remove();
            }

        } catch (error) {
            console.error('Failed to resolve conflict:', error);
        }
    }

    async sendMessageToSW(message) {
        return new Promise((resolve) => {
            const channel = new MessageChannel();

            channel.port1.onmessage = () => {
                resolve();
            };

            if (navigator.serviceWorker.controller) {
                navigator.serviceWorker.controller.postMessage(message, [channel.port2]);
            } else {
                resolve();
            }
        });
    }

    setupPeriodicSync() {
        // Register for periodic sync if supported
        if ('serviceWorker' in navigator && 'periodicSync' in window) {
            navigator.serviceWorker.ready.then(registration => {
                if ('periodicSync' in registration) {
                    registration.periodicSync.register('periodic-data-sync', {
                        minInterval: 24 * 60 * 60 * 1000 // 24 hours
                    }).catch(error => {
                        console.log('Periodic sync registration failed:', error);
                    });
                }
            });
        }
    }

    async triggerSync() {
        // Automatically sync when coming online
        if (this.isOnline && !this.syncInProgress) {
            try {
                await this.performSync();
                this.updateSyncStatus('online');
            } catch (error) {
                console.error('Auto sync failed:', error);
                this.updateSyncStatus('error');
            }
        }
    }

    updateNetworkQuality(quality) {
        const networkEl = document.getElementById('networkQualityIndicator');
        if (!networkEl) return;

        networkEl.className = 'network-quality';

        switch(quality) {
            case 'good':
                networkEl.classList.add('good');
                networkEl.textContent = 'Fast';
                networkEl.style.display = 'block';
                break;
            case 'poor':
                networkEl.classList.add('poor');
                networkEl.textContent = 'Slow';
                networkEl.style.display = 'block';
                break;
            case 'offline':
                networkEl.classList.add('offline');
                networkEl.textContent = 'Offline';
                networkEl.style.display = 'block';
                break;
            default:
                networkEl.style.display = 'none';
        }
    }

    async measureNetworkQuality() {
        if (!this.isOnline) {
            this.updateNetworkQuality('offline');
            return;
        }

        try {
            const startTime = Date.now();
            const response = await fetch('/static/schools/images/icon-192.png', {
                method: 'HEAD',
                cache: 'no-cache'
            });
            const endTime = Date.now();
            const latency = endTime - startTime;

            if (response.ok) {
                if (latency < 500) {
                    this.updateNetworkQuality('good');
                } else {
                    this.updateNetworkQuality('poor');
                }
            } else {
                this.updateNetworkQuality('poor');
            }
        } catch (error) {
            this.updateNetworkQuality('offline');
        }
    }
}

// Initialize PWA when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.pwa = new SchoolSyncPWA();

    // Measure network quality periodically
    setInterval(() => {
        window.pwa.measureNetworkQuality();
    }, 30000); // Every 30 seconds

    // Initial network quality measurement
    setTimeout(() => {
        window.pwa.measureNetworkQuality();
    }, 1000);
});
