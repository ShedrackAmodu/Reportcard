/**
 * Enhanced PWA Installation System
 * Provides smart installation prompting and state management
 */

class PWAInstaller {
    constructor() {
        this.deferredPrompt = null;
        this.isInstallable = false;
        this.isInstalled = false;
        this.installState = this.getInstallState();
        this.installAttempts = 0;
        this.maxInstallAttempts = 3;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkInstallationStatus();
        this.setupSmartPrompting();
    }

    setupEventListeners() {
        // Listen for the beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.isInstallable = true;
            this.installState.status = 'installable';
            this.saveInstallState();
            this.showSmartPrompt();
            this.showInstallButton();
        });

        // Listen for successful installation
        window.addEventListener('appinstalled', (e) => {
            this.isInstalled = true;
            this.installState.status = 'installed';
            this.installState.installedAt = new Date().toISOString();
            this.saveInstallState();
            this.hideInstallButton();
            this.showInstallationSuccess();
            this.trackInstallation('success');
        });

        // Listen for page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.isInstallable && !this.isInstalled) {
                this.checkInstallability();
            }
        });
    }

    checkInstallationStatus() {
        // Check if already installed
        if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
            this.isInstalled = true;
            this.installState.status = 'installed';
            this.saveInstallState();
            this.hideInstallButton();
            return;
        }

        // Check if user previously dismissed installation
        if (this.installState.status === 'dismissed' && this.shouldShowAgain()) {
            this.installState.status = 'pending';
            this.saveInstallState();
        }

        // Check if PWA is already installed via getInstalledRelatedApps
        if ('getInstalledRelatedApps' in navigator) {
            navigator.getInstalledRelatedApps().then(relatedApps => {
                const isInstalled = relatedApps.some(app => app.url === window.location.origin);
                if (isInstalled) {
                    this.isInstalled = true;
                    this.installState.status = 'installed';
                    this.saveInstallState();
                    this.hideInstallButton();
                }
            }).catch(() => {
                // Ignore errors
            });
        }
    }

    setupSmartPrompting() {
        // Smart timing for installation prompts
        setTimeout(() => {
            if (this.isInstallable && !this.isInstalled && this.shouldShowPrompt()) {
                this.showSmartPrompt();
            }
        }, 5000); // Show after 5 seconds

        // Show prompt on scroll
        let scrollTriggered = false;
        window.addEventListener('scroll', () => {
            if (!scrollTriggered && window.scrollY > 100 && this.isInstallable && !this.isInstalled && this.shouldShowPrompt()) {
                scrollTriggered = true;
                setTimeout(() => this.showSmartPrompt(), 1000);
            }
        });

        // Show prompt on exit intent
        let exitIntentTriggered = false;
        document.addEventListener('mouseleave', (e) => {
            if (!exitIntentTriggered && e.clientY <= 0 && this.isInstallable && !this.isInstalled && this.shouldShowPrompt()) {
                exitIntentTriggered = true;
                setTimeout(() => this.showSmartPrompt('exit'), 500);
            }
        });
    }

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

    shouldShowAgain() {
        const lastDismissed = new Date(this.installState.lastDismissed || 0);
        const daysSinceDismissed = (Date.now() - lastDismissed.getTime()) / (1000 * 60 * 60 * 24);
        return daysSinceDismissed >= 7; // Show again after 7 days
    }

    showSmartPrompt(type = 'default') {
        if (!this.isInstallable || this.isInstalled) return;

        this.installAttempts++;
        
        // Create different prompt types
        switch (type) {
            case 'exit':
                this.showExitIntentPrompt();
                break;
            case 'scroll':
                this.showScrollPrompt();
                break;
            default:
                this.showDefaultPrompt();
        }
    }

    showDefaultPrompt() {
        // Show installation banner
        this.showInstallationBanner();
    }

    showExitIntentPrompt() {
        // Show modal for exit intent
        this.showInstallationModal('Install Our App', 
            'Get the best experience with our app. Install now for offline access and faster performance.',
            'Install Now', 'Maybe Later');
    }

    showScrollPrompt() {
        // Show floating action button
        this.showFloatingInstallButton();
    }

    showInstallationBanner() {
        const banner = document.createElement('div');
        banner.id = 'pwa-install-banner';
        banner.className = 'pwa-banner position-fixed bottom-0 start-0 end-0 bg-gradient text-white shadow-lg';
        banner.style.cssText = `
            z-index: 99999;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            animation: slideUp 0.3s ease-out;
            backdrop-filter: blur(10px);
        `;

        banner.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="bg-white rounded-circle d-flex align-items-center justify-content-center me-3" style="width: 48px; height: 48px;">
                    <i class="bi bi-download text-primary fs-4"></i>
                </div>
                <div>
                    <div class="fw-bold">Install ReportCardApp</div>
                    <small>Get offline access and better performance</small>
                </div>
            </div>
            <div class="d-flex gap-2">
                <button class="btn btn-light btn-sm rounded-pill install-now-btn" onclick="pwaInstaller.installApp()">
                    <i class="bi bi-download me-1"></i>Install Now
                </button>
                <button class="btn btn-outline-light btn-sm rounded-pill dismiss-btn" onclick="pwaInstaller.dismissPrompt()">
                    <i class="bi bi-x me-1"></i>Not Now
                </button>
            </div>
        `;

        document.body.appendChild(banner);

        // Auto-hide after 10 seconds
        setTimeout(() => {
            if (banner.parentNode) {
                banner.style.animation = 'slideUpOut 0.3s ease-out';
                setTimeout(() => banner.remove(), 300);
            }
        }, 10000);
    }

    showInstallationModal(title, message, acceptText, declineText) {
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg">
                    <div class="modal-header bg-gradient text-white border-0">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close btn-close-white" onclick="pwaInstaller.dismissPrompt()"></button>
                    </div>
                    <div class="modal-body">
                        <div class="text-center mb-4">
                            <div class="bg-primary rounded-circle d-flex align-items-center justify-content-center mx-auto mb-3" style="width: 64px; height: 64px;">
                                <i class="bi bi-download text-white fs-1"></i>
                            </div>
                            <p>${message}</p>
                        </div>
                        <ul class="list-unstyled">
                            <li class="mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Offline access to your data</li>
                            <li class="mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Faster performance</li>
                            <li class="mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Push notifications</li>
                            <li class="mb-2"><i class="bi bi-check-circle-fill text-success me-2"></i>Home screen access</li>
                        </ul>
                    </div>
                    <div class="modal-footer border-0">
                        <button class="btn btn-gradient btn-lg w-100 install-now-btn" onclick="pwaInstaller.installApp()">
                            <i class="bi bi-download me-2"></i>${acceptText}
                        </button>
                        <button class="btn btn-outline-secondary w-100" onclick="pwaInstaller.dismissPrompt()">
                            ${declineText}
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden';
    }

    showFloatingInstallButton() {
        const button = document.createElement('button');
        button.id = 'floating-install-btn';
        button.className = 'btn btn-gradient position-fixed rounded-circle shadow-lg';
        button.style.cssText = `
            bottom: 20px;
            right: 20px;
            width: 56px;
            height: 56px;
            z-index: 99999;
            animation: bounce 2s infinite;
        `;
        button.innerHTML = '<i class="bi bi-download"></i>';
        button.onclick = () => this.installApp();

        document.body.appendChild(button);

        // Auto-hide after 15 seconds
        setTimeout(() => {
            if (button.parentNode) {
                button.style.animation = 'fadeOut 0.5s ease-out';
                setTimeout(() => button.remove(), 500);
            }
        }, 15000);
    }

    showInstallationSuccess() {
        // Show success toast
        showToast('App installed successfully! Enjoy offline access and better performance.', 'success');
        
        // Show success modal with onboarding
        setTimeout(() => {
            this.showSuccessModal();
        }, 2000);
    }

    showSuccessModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow-lg">
                    <div class="modal-header bg-success text-white border-0">
                        <h5 class="modal-title">Installation Complete!</h5>
                        <button type="button" class="btn-close btn-close-white" onclick="this.closest('.modal').remove()"></button>
                    </div>
                    <div class="modal-body text-center">
                        <div class="bg-success rounded-circle d-flex align-items-center justify-content-center mx-auto mb-3" style="width: 64px; height: 64px;">
                            <i class="bi bi-check-lg text-white fs-1"></i>
                        </div>
                        <h6 class="text-success">Your app is now installed!</h6>
                        <p class="text-muted">You can now access ReportCardApp from your home screen.</p>
                        <div class="row mt-4">
                            <div class="col-md-6">
                                <div class="card h-100">
                                    <div class="card-body">
                                        <i class="bi bi-phone text-primary fs-2 mb-2"></i>
                                        <h6>Mobile</h6>
                                        <p class="small text-muted">Find the app icon on your home screen</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card h-100">
                                    <div class="card-body">
                                        <i class="bi bi-laptop text-info fs-2 mb-2"></i>
                                        <h6>Desktop</h6>
                                        <p class="small text-muted">Check your applications folder</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer border-0">
                        <button class="btn btn-success w-100" onclick="this.closest('.modal').remove()">
                            <i class="bi bi-check-circle me-2"></i>Got it!
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden';
    }

    async installApp() {
        if (!this.deferredPrompt) {
            showToast('Installation not available at this time.', 'warning');
            return;
        }

        try {
            this.trackInstallation('started');
            
            // Show installing state
            const buttons = document.querySelectorAll('.install-now-btn, .install-app-btn');
            buttons.forEach(btn => {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Installing...';
            });

            const result = await this.deferredPrompt.prompt();
            
            if (result.outcome === 'accepted') {
                this.trackInstallation('accepted');
                showToast('Installing app...', 'info');
            } else {
                this.trackInstallation('cancelled');
                showToast('Installation cancelled.', 'warning');
                this.dismissPrompt();
            }

            this.deferredPrompt = null;
            
            // Reset button states
            buttons.forEach(btn => {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-download me-1"></i>Install Now';
            });

        } catch (error) {
            console.error('Installation error:', error);
            this.trackInstallation('error', error.message);
            showToast('Installation failed. Please try again.', 'error');
        }
    }

    dismissPrompt() {
        this.installState.status = 'dismissed';
        this.installState.lastDismissed = new Date().toISOString();
        this.installState.dismissCount = (this.installState.dismissCount || 0) + 1;
        this.saveInstallState();

        // Remove any visible prompts
        const banner = document.getElementById('pwa-install-banner');
        if (banner) banner.remove();

        const modal = document.querySelector('.modal.show');
        if (modal) modal.remove();

        const floatingBtn = document.getElementById('floating-install-btn');
        if (floatingBtn) floatingBtn.remove();

        document.body.style.overflow = 'auto';
    }

    showInstallButton() {
        const installButtons = document.querySelectorAll('.install-app-btn');
        installButtons.forEach(button => {
            button.style.display = 'inline-block';
            button.classList.remove('d-none');
            button.classList.remove('installed');
            button.classList.remove('installing');
            button.textContent = 'Install App';
            button.disabled = false;
        });
    }

    hideInstallButton() {
        const installButtons = document.querySelectorAll('.install-app-btn');
        installButtons.forEach(button => {
            button.style.display = 'none';
        });
    }

    checkInstallability() {
        if (this.isInstalled || this.installState.status === 'installed') return;

        // Additional checks for installability
        const isHTTPS = location.protocol === 'https:' || location.hostname === 'localhost';
        const hasManifest = !!document.querySelector('link[rel="manifest"]');
        const hasServiceWorker = 'serviceWorker' in navigator;

        if (isHTTPS && hasManifest && hasServiceWorker) {
            this.isInstallable = true;
            this.installState.status = 'installable';
            this.saveInstallState();
        }
    }

    getInstallState() {
        try {
            const saved = localStorage.getItem('pwa_install_state');
            return saved ? JSON.parse(saved) : {
                status: 'pending',
                installedAt: null,
                lastDismissed: null,
                dismissCount: 0,
                installAttempts: 0
            };
        } catch (e) {
            return {
                status: 'pending',
                installedAt: null,
                lastDismissed: null,
                dismissCount: 0,
                installAttempts: 0
            };
        }
    }

    saveInstallState() {
        localStorage.setItem('pwa_install_state', JSON.stringify(this.installState));
    }

    trackInstallation(action, details = null) {
        // Track installation events for analytics
        const eventData = {
            action: action,
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            details: details,
            installState: this.installState
        };

        console.log('PWA Installation Event:', eventData);

        // Send to analytics if available
        if (window.gtag) {
            window.gtag('event', 'pwa_install', {
                event_category: 'PWA',
                event_label: action,
                value: 1
            });
        }

        // Send to server for tracking
        if (navigator.sendBeacon) {
            try {
                const data = JSON.stringify(eventData);
                navigator.sendBeacon('/api/pwa-tracking/', data);
            } catch (e) {
                // Ignore tracking errors
            }
        }
    }
}

// Initialize PWA Installer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.pwaInstaller = new PWAInstaller();
});

// Add CSS animations for PWA installer
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from { transform: translateY(100%); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    
    @keyframes slideUpOut {
        from { transform: translateY(0); opacity: 1; }
        to { transform: translateY(100%); opacity: 0; }
    }
    
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
        40% { transform: translateY(-10px); }
        60% { transform: translateY(-5px); }
    }
    
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    
    .pwa-banner {
        animation: slideUp 0.3s ease-out;
    }
    
    .btn-gradient {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        color: white;
        transition: all 0.3s ease;
    }
    
    .btn-gradient:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }
    
    .bg-gradient {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .modal-backdrop.show {
        opacity: 0.8;
    }
    
    .modal.show {
        background-color: rgba(0, 0, 0, 0.5);
    }
`;
document.head.appendChild(style);

// Global helper functions
function showToast(message, type = 'info') {
    const toastId = 'toast-' + Date.now();
    const toastContainer = document.getElementById('toast-container') || (() => {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '99999';
        document.body.appendChild(container);
        return container;
    })();
    
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    const icons = {
        success: 'bi-check-circle-fill',
        error: 'bi-exclamation-triangle-fill',
        warning: 'bi-exclamation-circle-fill',
        info: 'bi-info-circle-fill'
    };
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi ${icons[type] || 'bi-info-circle-fill'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: 4000 });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Make functions globally available
window.installApp = () => {
    if (window.pwaInstaller) {
        window.pwaInstaller.installApp();
    }
};

window.dismissPrompt = () => {
    if (window.pwaInstaller) {
        window.pwaInstaller.dismissPrompt();
    }
};