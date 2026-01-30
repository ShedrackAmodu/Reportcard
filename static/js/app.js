// ReportCardApp PWA Client-side JavaScript
class ReportCardAppPWA {
    constructor() {
        this.isOnline = navigator.onLine;
        this.syncInProgress = false;
        this.pullToRefreshEnabled = false;
        this.touchStartY = 0;
        this.installPrompt = null;
        this.isInstallable = false;
        this.isInstalled = false;

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
        this.setupPWAInstall();

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

        // Also handle online form submissions to update cache
        document.addEventListener('submit', async (e) => {
            const form = e.target;
            if (this.isOnline && form.dataset.offline !== 'false') {
                // Allow normal submission but also prepare for potential cache updates
                // The service worker will handle caching API responses
            }
        });
    }

    async handleOfflineSubmission(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        // Determine the model type from form action or data attributes
        const model = form.dataset.model || this.guessModelFromForm(form);

        // Add to pending operations with enhanced metadata
        const operation = {
            type: 'form_submission',
            model: model,
            url: form.action,
            method: form.method || 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': this.getCsrfToken(),
                'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
            },
            body: new URLSearchParams(data).toString(),
            timestamp: Date.now(),
            formData: data
        };

        try {
            await this.addPendingOperation(operation);
            this.showOfflineNotification('Form saved offline. Will sync when online.');
            form.reset();

            // Add visual indicator to the form
            this.addOfflineIndicatorToForm(form);
        } catch (error) {
            console.error('Failed to save offline:', error);
            this.showOfflineNotification('Failed to save offline. Please try again.', 'error');
        }
    }

    guessModelFromForm(form) {
        // Try to determine model from form action URL
        const action = form.action;
        if (action.includes('/grades/')) return 'grades';
        if (action.includes('/attendance/')) return 'attendance';
        if (action.includes('/users/')) return 'users';
        if (action.includes('/class-sections/')) return 'classSections';
        if (action.includes('/subjects/')) return 'subjects';
        return 'unknown';
    }

    addOfflineIndicatorToForm(form) {
        // Add a small indicator to show this form has offline data
        const indicator = document.createElement('small');
        indicator.className = 'text-warning ms-2';
        indicator.textContent = '(saved offline)';

        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn) {
            submitBtn.parentNode.insertBefore(indicator, submitBtn.nextSibling);
            setTimeout(() => indicator.remove(), 3000); // Remove after 3 seconds
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
        // Load cached data for offline viewing and hybrid online/offline mode
        const tables = document.querySelectorAll('table[data-model]');
        for (const table of tables) {
            const model = table.dataset.model;
            await this.loadTableFromCache(table, model);
        }

        // Also try to load data from API if online
        if (this.isOnline) {
            this.loadLiveData();
        }
    }

    async loadLiveData() {
        // Load fresh data from API and update cache
        const tables = document.querySelectorAll('table[data-model]');
        for (const table of tables) {
            const model = table.dataset.model;
            const apiUrl = this.getApiUrlForModel(model);

            if (apiUrl) {
                try {
                    const response = await fetch(apiUrl, {
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    if (response.ok) {
                        const data = await response.json();
                        // Update cache with fresh data
                        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                            navigator.serviceWorker.controller.postMessage({
                                type: 'CACHE_API_RESPONSE',
                                url: apiUrl,
                                data: data,
                                model: model
                            });
                        }
                    }
                } catch (error) {
                    console.log('Failed to load live data for', model, error);
                }
            }
        }
    }

    getApiUrlForModel(model) {
        const modelUrls = {
            'grades': '/api/grades/',
            'attendance': '/api/attendance/',
            'users': '/api/users/',
            'classSections': '/api/class-sections/',
            'subjects': '/api/subjects/'
        };
        return modelUrls[model];
    }

    async loadTableFromCache(table, model) {
        try {
            const cachedData = await this.getCachedData(model);
            if (cachedData && cachedData.length > 0) {
                this.populateTable(table, cachedData);
                if (!this.isOnline) {
                    table.classList.add('offline-indicator');
                }
            } else if (!this.isOnline) {
                // Show no data message when offline and no cache
                this.showNoOfflineData(table, model);
            }
        } catch (error) {
            console.error('Failed to load cached data:', error);
            if (!this.isOnline) {
                this.showNoOfflineData(table, model);
            }
        }
    }

    showNoOfflineData(table, model) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="100%" class="text-center text-muted py-4">
                    <i class="bi bi-wifi-off fs-3 d-block mb-2"></i>
                    <strong>No cached data available</strong><br>
                    <small>Connect to internet to load ${model} data</small>
                </td>
            </tr>
        `;
        table.classList.add('offline-indicator');
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
            const response = await fetch('/static/images/logo.png', {
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

    setupPWAInstall() {
        // Check if already installed
        if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone) {
            this.isInstalled = true;
            return;
        }

        // Listen for the beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.installPrompt = e;
            this.isInstallable = true;
            this.showInstallButtons();
        });

        // Listen for successful installation
        window.addEventListener('appinstalled', (e) => {
            this.isInstalled = true;
            this.installPrompt = null;
            this.isInstallable = false;
            this.hideInstallButtons();
            this.showOfflineNotification('App installed successfully!', 'success');
        });

        // Check if installable after a delay (fallback)
        setTimeout(() => {
            if (!this.isInstallable && !this.isInstalled && 'onbeforeinstallprompt' in window) {
                this.checkInstallability();
            }
        }, 3000);
    }

    async checkInstallability() {
        // Fallback check for installability
        if ('getInstalledRelatedApps' in navigator) {
            try {
                const relatedApps = await navigator.getInstalledRelatedApps();
                const isRelatedAppInstalled = relatedApps.some(app => app.url === window.location.origin);

                if (!isRelatedAppInstalled) {
                    this.isInstallable = true;
                    this.showInstallButtons();
                }
            } catch (error) {
                console.log('Related apps check failed:', error);
            }
        }
    }

    showInstallButtons() {
        const installButtons = document.querySelectorAll('.install-app-btn');
        installButtons.forEach(button => {
            button.style.display = 'inline-block';
            button.disabled = false;
            button.textContent = 'Install App';
            button.onclick = () => this.installApp();
        });
    }

    hideInstallButtons() {
        const installButtons = document.querySelectorAll('.install-app-btn');
        installButtons.forEach(button => {
            button.style.display = 'none';
        });
    }

    async installApp() {
        if (!this.installPrompt) {
            this.showOfflineNotification('Installation not available at this time.', 'error');
            return;
        }

        try {
            const result = await this.installPrompt.prompt();
            const choiceResult = await this.installPrompt.userChoice;

            if (choiceResult.outcome === 'accepted') {
                this.showOfflineNotification('Installing...', 'success');
            } else {
                this.showOfflineNotification('Installation cancelled.', 'error');
            }

            this.installPrompt = null;
        } catch (error) {
            console.error('Installation failed:', error);
            this.showOfflineNotification('Installation failed. Please try again.', 'error');
        }
    }
}

// Store user context in service worker when user data is available
async function storeUserContextInSW() {
    // Try to get user data from Django context or localStorage
    let userData = null;

    // Check if we have user data in a global variable (set by Django template)
    if (typeof window.userData !== 'undefined') {
        userData = window.userData;
    } else {
        // Try to get from localStorage or other sources
        const token = localStorage.getItem('access_token') || localStorage.getItem('token');
        if (token) {
            userData = { token: token };
        }
    }

    if (userData && userData.token) {
        // Extract school ID if available
        let schoolId = null;
        if (userData.school_id) {
            schoolId = userData.school_id;
        } else if (typeof window.schoolId !== 'undefined') {
            schoolId = window.schoolId;
        }

        const context = {
            token: userData.token,
            userId: userData.id,
            schoolId: schoolId,
            role: userData.role
        };

        // Store in service worker
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
                type: 'STORE_USER_CONTEXT',
                data: context
            });
        }
    }
}

// Initialize PWA when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.pwa = new ReportCardAppPWA();

    // Store user context for offline sync
    storeUserContextInSW();

    // Measure network quality periodically
    setInterval(() => {
        window.pwa.measureNetworkQuality();
    }, 30000); // Every 30 seconds

    // Initial network quality measurement
    setTimeout(() => {
        window.pwa.measureNetworkQuality();
    }, 1000);
});
