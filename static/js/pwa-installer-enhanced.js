/**
 * Enhanced PWA Installation System
 * Automated PWA installation with download tracking
 */

class PWAInstallerEnhanced {
    constructor() {
        this.deferredPrompt = null;
        this.isInstallable = false;
        this.isInstalled = false;
        this.installState = this.getInstallState();
        this.installAttempts = 0;
        this.maxInstallAttempts = 3;
        this.userAgent = navigator.userAgent;
        
        this.init();
    }

    /**
     * Initialize PWA installer
     */
    init() {
        console.log('[PWA] Initializing PWA Installer Enhanced');
        this.setupEventListeners();
        this.checkInstallationStatus();
        this.setupAutoInstall();
        this.registerServiceWorker();
    }

    /**
     * Register service worker
     */
    registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js', { scope: '/' })
                .then(registration => {
                    console.log('[PWA] Service Worker registered:', registration);
                    this.trackPWAStatus('sw_registered');
                })
                .catch(error => {
                    console.error('[PWA] Service Worker registration failed:', error);
                    this.trackPWAStatus('sw_failed', error);
                });
        }
    }

    /**
     * Setup event listeners for installation
     */
    setupEventListeners() {
        // Listen for the beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('[PWA] beforeinstallprompt event fired');
            e.preventDefault();
            this.deferredPrompt = e;
            this.isInstallable = true;
            this.installState.status = 'installable';
            this.saveInstallState();
            this.trackPWAStatus('installable_detected');
            this.showSmartPrompt();
            this.showInstallButton();
        });

        // Listen for successful installation
        window.addEventListener('appinstalled', (e) => {
            console.log('[PWA] App installed successfully');
            this.isInstalled = true;
            this.installState.status = 'installed';
            this.installState.installedAt = new Date().toISOString();
            this.saveInstallState();
            this.hideInstallButton();
            this.showInstallationSuccess();
            this.trackInstallation('pwa_success');
        });

        // Listen for page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.isInstallable && !this.isInstalled) {
                console.log('[PWA] Page became visible, checking installability');
                this.checkInstallability();
            }
        });
    }

    /**
     * Check current installation status
     */
    checkInstallationStatus() {
        // Check if already installed via standalone mode
        if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
            console.log('[PWA] App is in standalone mode (installed)');
            this.isInstalled = true;
            this.installState.status = 'installed';
            this.saveInstallState();
            this.hideInstallButton();
            return;
        }

        // Check if previously dismissed
        if (this.installState.status === 'dismissed' && this.shouldShowAgain()) {
            this.installState.status = 'pending';
            this.saveInstallState();
        }

        // Check installed related apps API
        if ('getInstalledRelatedApps' in navigator) {
            navigator.getInstalledRelatedApps()
                .then(relatedApps => {
                    const isInstalled = relatedApps.some(app => app.url === window.location.origin);
                    if (isInstalled) {
                        console.log('[PWA] App found in installed apps');
                        this.isInstalled = true;
                        this.installState.status = 'installed';
                        this.saveInstallState();
                        this.hideInstallButton();
                    }
                })
                .catch(() => {
                    console.log('[PWA] getInstalledRelatedApps not available');
                });
        }
    }

    /**
     * Setup automatic installation for supported platforms
     */
    setupAutoInstall() {
        // Auto-install on supported mobile platforms
        setTimeout(() => {
            if (this.isInstallable && !this.isInstalled && this.shouldShowPrompt()) {
                console.log('[PWA] Setting up auto-install...');
                
                // Check device type
                if (this.isMobileDevice()) {
                    this.attemptAutoInstall();
                } else {
                    this.showSmartPrompt('desktop');
                }
            }
        }, 3000);
    }

    /**
     * Attempt automatic installation
     */
    attemptAutoInstall() {
        console.log('[PWA] Attempting auto-install on mobile device');
        
        if (this.installAttempts >= this.maxInstallAttempts) {
            console.log('[PWA] Max install attempts reached');
            return;
        }

        // Show installation guidance
        this.showInstallationGuidance();
    }

    /**
     * Check device type
     */
    isMobileDevice() {
        const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
        return mobileRegex.test(this.userAgent);
    }

    /**
     * Get device platform
     */
    getDevicePlatform() {
        if (/Android/i.test(this.userAgent)) return 'android';
        if (/iPhone|iPad|iPod/i.test(this.userAgent)) return 'ios';
        if (/Windows/i.test(this.userAgent)) return 'windows';
        if (/Mac/i.test(this.userAgent)) return 'macos';
        if (/Linux/i.test(this.userAgent)) return 'linux';
        return 'unknown';
    }

    /**
     * Show installation guidance
     */
    showInstallationGuidance() {
        const platform = this.getDevicePlatform();
        let message = '';
        let downloadUrl = '';

        switch (platform) {
            case 'android':
                message = 'Install our Android app for the best experience!';
                downloadUrl = '/download/apk/?type=android';
                break;
            case 'ios':
                message = 'Install our iOS app from the App Store!';
                downloadUrl = '/download/apk/?type=ios';
                break;
            case 'windows':
                message = 'Install our Windows app for seamless integration!';
                downloadUrl = '/download/apk/?type=windows';
                break;
            default:
                message = 'Install our app for better experience!';
                downloadUrl = '/download/apk/?type=android';
        }

        this.showInstallationModal(message, downloadUrl);
    }

    /**
     * Install the app
     */
    installApp() {
        console.log('[PWA] Install app triggered');

        if (this.deferredPrompt) {
            // Show PWA install prompt
            this.deferredPrompt.prompt();
            this.deferredPrompt.userChoice
                .then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('[PWA] User accepted installation prompt');
                        this.trackInstallation('pwa_accepted');
                    } else {
                        console.log('[PWA] User dismissed installation prompt');
                        this.trackInstallation('pwa_dismissed');
                        this.dismissPrompt();
                    }
                    this.deferredPrompt = null;
                })
                .catch(err => {
                    console.error('[PWA] Installation error:', err);
                    this.trackInstallation('pwa_error', err);
                });
        } else if (this.isMobileDevice()) {
            // Offer native app download
            this.showDownloadOptions();
        }
    }

    /**
     * Show download options for native apps
     */
    showDownloadOptions() {
        const platform = this.getDevicePlatform();
        
        const downloadModal = document.createElement('div');
        downloadModal.className = 'modal fade show';
        downloadModal.id = 'download-options-modal';
        downloadModal.style.display = 'block';
        downloadModal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg">
                    <div class="modal-header bg-gradient text-white border-0">
                        <h5 class="modal-title">Download App</h5>
                        <button type="button" class="btn-close btn-close-white" onclick="this.closest('.modal').remove()"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-4">
                            <div class="bg-primary rounded-circle d-flex align-items-center justify-content-center mx-auto mb-3" style="width: 64px; height: 64px;">
                                <i class="bi bi-download text-white fs-1"></i>
                            </div>
                            <h6>Get ReportCardApp on Your Device</h6>
                        </div>
                        <div class="d-grid gap-2">
                            <a href="/download/apk/?type=android" class="btn btn-outline-primary btn-lg" download>
                                <i class="bi bi-android2 me-2"></i>Download for Android
                            </a>
                            <a href="/download/apk/?type=ios" class="btn btn-outline-primary btn-lg" download>
                                <i class="bi bi-apple me-2"></i>Download for iOS
                            </a>
                            <a href="/download/apk/?type=windows" class="btn btn-outline-primary btn-lg" download>
                                <i class="bi bi-windows me-2"></i>Download for Windows
                            </a>
                        </div>
                    </div>
                    <div class="modal-footer border-0">
                        <button type="button" class="btn btn-secondary w-100" onclick="this.closest('.modal').remove()">Close</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(downloadModal);
        this.trackPWAStatus('download_options_shown');
    }

    /**
     * Show smart prompt
     */
    showSmartPrompt(type = 'default') {
        if (!this.isInstallable || this.isInstalled) return;

        this.installAttempts++;

        switch (type) {
            case 'exit':
                this.showExitIntentPrompt();
                break;
            case 'scroll':
                this.showScrollPrompt();
                break;
            case 'desktop':
                this.showDesktopPrompt();
                break;
            default:
                this.showInstallationBanner();
        }
    }

    /**
     * Show exit intent prompt
     */
    showExitIntentPrompt() {
        this.showInstallationModal(
            'Install Our App',
            'Get offline access, push notifications, and faster performance. Install now!',
            'Install Now',
            'Maybe Later'
        );
    }

    /**
     * Show scroll prompt
     */
    showScrollPrompt() {
        this.showFloatingInstallButton();
    }

    /**
     * Show desktop prompt
     */
    showDesktopPrompt() {
        this.showInstallationBanner();
    }

    /**
     * Show installation banner
     */
    showInstallationBanner() {
        if (document.getElementById('pwa-install-banner')) return;

        const banner = document.createElement('div');
        banner.id = 'pwa-install-banner';
        banner.className = 'pwa-banner position-fixed bottom-0 start-0 end-0 bg-gradient text-white shadow-lg';
        banner.style.cssText = `
            z-index: 99999;
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            animation: slideUp 0.3s ease-out;
            backdrop-filter: blur(10px);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        `;

        banner.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="bg-white rounded-circle d-flex align-items-center justify-content-center me-3" style="width: 48px; height: 48px; flex-shrink: 0;">
                    <i class="bi bi-download text-primary fs-5"></i>
                </div>
                <div>
                    <div class="fw-bold mb-0">Install ReportCardApp</div>
                    <small>Offline access + faster performance</small>
                </div>
            </div>
            <div class="d-flex gap-2">
                <button class="btn btn-light btn-sm rounded-pill install-now-btn" onclick="pwaInstaller.installApp()">
                    <i class="bi bi-download me-1"></i>Install
                </button>
                <button class="btn btn-outline-light btn-sm rounded-pill dismiss-btn" onclick="pwaInstaller.dismissPrompt()">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;

        document.body.appendChild(banner);
        this.trackPWAStatus('banner_shown');

        // Auto-hide after 8 seconds
        setTimeout(() => {
            if (banner.parentNode) {
                banner.style.animation = 'slideDown 0.3s ease-out';
                setTimeout(() => banner.remove(), 300);
            }
        }, 8000);
    }

    /**
     * Show floating install button
     */
    showFloatingInstallButton() {
        if (document.getElementById('floating-install-btn')) return;

        const button = document.createElement('button');
        button.id = 'floating-install-btn';
        button.className = 'btn btn-primary position-fixed rounded-circle shadow-lg';
        button.style.cssText = `
            bottom: 20px;
            right: 20px;
            width: 56px;
            height: 56px;
            z-index: 99999;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: bounce 2s infinite;
            border: none;
        `;
        button.innerHTML = '<i class="bi bi-download fs-5"></i>';
        button.onclick = () => this.installApp();
        button.title = 'Install app';

        document.body.appendChild(button);

        // Auto-hide after 15 seconds
        setTimeout(() => {
            if (button.parentNode) {
                button.style.animation = 'fadeOut 0.5s ease-out';
                setTimeout(() => button.remove(), 500);
            }
        }, 15000);
    }

    /**
     * Show installation modal
     */
    showInstallationModal(message, downloadUrl = null) {
        if (document.getElementById('pwa-install-modal')) return;

        const modal = document.createElement('div');
        modal.id = 'pwa-install-modal';
        modal.className = 'modal fade show';
        modal.style.cssText = 'display: block; background-color: rgba(0,0,0,0.5);';
        
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg">
                    <div class="modal-header bg-gradient text-white border-0">
                        <h5 class="modal-title">Install ReportCardApp</h5>
                        <button type="button" class="btn-close btn-close-white" onclick="pwaInstaller.dismissPrompt()"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-4">
                            <div class="bg-primary rounded-circle d-flex align-items-center justify-content-center mx-auto mb-3" style="width: 64px; height: 64px;">
                                <i class="bi bi-download text-white fs-1"></i>
                            </div>
                            <p class="mb-0">${message}</p>
                        </div>
                        <ul class="list-unstyled">
                            <li class="mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Offline access to your data</li>
                            <li class="mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Faster performance</li>
                            <li class="mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Push notifications</li>
                            <li class="mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Home screen icon</li>
                        </ul>
                    </div>
                    <div class="modal-footer border-0 gap-2">
                        <button class="btn btn-outline-secondary flex-grow-1" onclick="pwaInstaller.dismissPrompt()">
                            Not Now
                        </button>
                        <button class="btn btn-primary flex-grow-1" onclick="pwaInstaller.installApp()">
                            <i class="bi bi-download me-2"></i>Install Now
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden';
        this.trackPWAStatus('modal_shown');
    }

    /**
     * Show installation success
     */
    showInstallationSuccess() {
        const successModal = document.createElement('div');
        successModal.className = 'modal fade show';
        successModal.style.cssText = 'display: block; background-color: rgba(0,0,0,0.5);';
        successModal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg">
                    <div class="modal-header bg-success text-white border-0">
                        <h5 class="modal-title">App Installed!</h5>
                    </div>
                    <div class="modal-body text-center py-4">
                        <div class="bg-success rounded-circle d-flex align-items-center justify-content-center mx-auto mb-3" style="width: 80px; height: 80px;">
                            <i class="bi bi-check-lg text-white fs-1"></i>
                        </div>
                        <h6>Installation Successful</h6>
                        <p class="text-muted mb-0">You can now access ReportCardApp from your home screen and use it offline!</p>
                    </div>
                    <div class="modal-footer border-0">
                        <button type="button" class="btn btn-success w-100" onclick="this.closest('.modal').remove()">Got it!</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(successModal);
        setTimeout(() => successModal.remove(), 5000);
    }

    /**
     * Dismiss prompt
     */
    dismissPrompt() {
        console.log('[PWA] Prompt dismissed');
        this.installState.status = 'dismissed';
        this.installState.lastDismissed = new Date().toISOString();
        this.saveInstallState();
        this.trackPWAStatus('prompt_dismissed');

        // Remove modals and banners
        const elements = ['pwa-install-banner', 'pwa-install-modal', 'floating-install-btn'];
        elements.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.remove();
        });
        document.body.style.overflow = '';
    }

    /**
     * Show install button in navbar/header
     */
    showInstallButton() {
        const installBtn = document.getElementById('pwa-install-header-btn');
        if (installBtn) {
            installBtn.style.display = 'block';
            installBtn.onclick = () => this.installApp();
        }
    }

    /**
     * Hide install button
     */
    hideInstallButton() {
        const installBtn = document.getElementById('pwa-install-header-btn');
        if (installBtn) {
            installBtn.style.display = 'none';
        }
    }

    /**
     * Check installability
     */
    checkInstallability() {
        if (this.isInstallable && !this.isInstalled && this.shouldShowPrompt()) {
            this.showSmartPrompt();
        }
    }

    /**
     * Get install state from localStorage
     */
    getInstallState() {
        const state = localStorage.getItem('pwa_install_state');
        return state ? JSON.parse(state) : {
            status: 'pending',
            attempts: 0,
            lastDismissed: null,
            installedAt: null
        };
    }

    /**
     * Save install state to localStorage
     */
    saveInstallState() {
        localStorage.setItem('pwa_install_state', JSON.stringify(this.installState));
    }

    /**
     * Determine if prompt should be shown
     */
    shouldShowPrompt() {
        if (this.isInstalled || this.installState.status === 'installed') {
            return false;
        }

        if (this.installState.status === 'dismissed') {
            return this.shouldShowAgain();
        }

        if (this.installState.status === 'installable' && this.installAttempts >= this.maxInstallAttempts) {
            return false;
        }

        return true;
    }

    /**
     * Check if should show prompt again after dismissal
     */
    shouldShowAgain() {
        const lastDismissed = new Date(this.installState.lastDismissed || 0);
        const daysSinceDismissed = (Date.now() - lastDismissed.getTime()) / (1000 * 60 * 60 * 24);
        return daysSinceDismissed >= 7; // Show again after 7 days
    }

    /**
     * Track installation event
     */
    trackInstallation(eventType, details = null) {
        console.log('[PWA] Tracking installation:', eventType, details);
        
        // Send to analytics API
        fetch('/api/pwa-tracking/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            },
            body: JSON.stringify({
                event_type: eventType,
                user_agent: this.userAgent,
                platform: this.getDevicePlatform(),
                timestamp: new Date().toISOString(),
                details: details
            })
        }).catch(err => console.error('[PWA] Tracking failed:', err));
    }

    /**
     * Track PWA status
     */
    trackPWAStatus(status, error = null) {
        console.log('[PWA] Status:', status, error);
        
        fetch('/api/pwa-status/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCookie('csrftoken')
            },
            body: JSON.stringify({
                status: status,
                error: error ? error.toString() : null,
                platform: this.getDevicePlatform(),
                timestamp: new Date().toISOString()
            })
        }).catch(err => console.error('[PWA] Status tracking failed:', err));
    }

    /**
     * Get CSRF token from cookies
     */
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Initialize PWA installer when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pwaInstaller = new PWAInstallerEnhanced();
    });
} else {
    window.pwaInstaller = new PWAInstallerEnhanced();
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from {
            transform: translateY(100%);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }

    @keyframes slideDown {
        from {
            transform: translateY(0);
            opacity: 1;
        }
        to {
            transform: translateY(100%);
            opacity: 0;
        }
    }

    @keyframes fadeOut {
        to {
            opacity: 0;
            transform: scale(0.9);
        }
    }

    @keyframes bounce {
        0%, 100% {
            transform: translateY(0);
        }
        50% {
            transform: translateY(-10px);
        }
    }

    .bg-gradient {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .btn-gradient {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
    }

    .btn-gradient:hover {
        background: linear-gradient(135deg, #5568d3 0%, #6a3a8f 100%);
        color: white;
    }

    .pwa-banner {
        border-top: 3px solid rgba(255, 255, 255, 0.3);
    }

    #pwa-install-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1050;
    }
`;
document.head.appendChild(style);
