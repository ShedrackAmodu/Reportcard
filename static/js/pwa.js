(function () {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/service-worker.js').catch(function (error) {
      console.warn('Service worker registration failed:', error);
    });
  });

  let deferredPrompt = null;
  const installBtn = document.getElementById('installAppBtn');

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    if (installBtn) {
      installBtn.classList.remove('d-none');
    }
  });

  if (installBtn) {
    installBtn.addEventListener('click', async function () {
      if (!deferredPrompt) {
        return;
      }
      deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      deferredPrompt = null;
      installBtn.classList.add('d-none');
    });
  }
})();

