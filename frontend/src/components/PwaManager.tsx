import { useEffect, useMemo, useState } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
}

type NavigatorWithStandalone = Navigator & { standalone?: boolean };

const INSTALL_DISMISSED_KEY = 'ptt-alert-hub-install-dismissed';
const UPDATE_CHECK_INTERVAL_MS = 60 * 60 * 1000;

function isStandaloneMode(): boolean {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    (navigator as NavigatorWithStandalone).standalone === true
  );
}

function isIosDevice(): boolean {
  return (
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  );
}

export function PwaManager() {
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [installDismissed, setInstallDismissed] = useState(
    () => sessionStorage.getItem(INSTALL_DISMISSED_KEY) === 'true',
  );
  const [showIosGuide, setShowIosGuide] = useState(false);
  const [updateRegistration, setUpdateRegistration] = useState<ServiceWorkerRegistration | null>(null);
  const [online, setOnline] = useState(navigator.onLine);
  const [installed, setInstalled] = useState(isStandaloneMode);

  const ios = useMemo(isIosDevice, []);
  const showInstallBanner = !installed && !installDismissed && (installPrompt !== null || ios);

  useEffect(() => {
    const handleBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as BeforeInstallPromptEvent);
    };
    const handleInstalled = () => {
      setInstallPrompt(null);
      setInstalled(true);
      sessionStorage.removeItem(INSTALL_DISMISSED_KEY);
    };
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    window.addEventListener('appinstalled', handleInstalled);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      window.removeEventListener('appinstalled', handleInstalled);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  useEffect(() => {
    if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return undefined;

    let disposed = false;
    let refreshing = false;
    let updateTimer: number | undefined;
    let checkForUpdate: (() => void) | undefined;

    const handleControllerChange = () => {
      if (refreshing) return;
      refreshing = true;
      window.location.reload();
    };

    navigator.serviceWorker.addEventListener('controllerchange', handleControllerChange);

    void navigator.serviceWorker
      .register('/sw.js', { scope: '/' })
      .then((registration) => {
        if (disposed) return;
        if (registration.waiting) setUpdateRegistration(registration);

        registration.addEventListener('updatefound', () => {
          const installingWorker = registration.installing;
          if (!installingWorker) return;
          installingWorker.addEventListener('statechange', () => {
            if (!disposed && installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
              setUpdateRegistration(registration);
            }
          });
        });

        checkForUpdate = () => {
          if (document.visibilityState === 'visible') {
            void registration.update().catch(() => undefined);
          }
        };
        updateTimer = window.setInterval(checkForUpdate, UPDATE_CHECK_INTERVAL_MS);
        document.addEventListener('visibilitychange', checkForUpdate);
      })
      .catch((error: unknown) => console.error('Service Worker 註冊失敗', error));

    return () => {
      disposed = true;
      navigator.serviceWorker.removeEventListener('controllerchange', handleControllerChange);
      if (checkForUpdate) document.removeEventListener('visibilitychange', checkForUpdate);
      if (updateTimer !== undefined) window.clearInterval(updateTimer);
    };
  }, []);

  const dismissInstall = () => {
    sessionStorage.setItem(INSTALL_DISMISSED_KEY, 'true');
    setInstallDismissed(true);
  };

  const handleInstall = async () => {
    if (installPrompt) {
      await installPrompt.prompt();
      const choice = await installPrompt.userChoice;
      if (choice.outcome === 'accepted') setInstallPrompt(null);
      return;
    }
    if (ios) setShowIosGuide(true);
  };

  const applyUpdate = () => {
    const waitingWorker = updateRegistration?.waiting;
    if (waitingWorker) {
      waitingWorker.postMessage({ type: 'SKIP_WAITING' });
      return;
    }
    window.location.reload();
  };

  return (
    <>
      <div className="c-pwa-stack" aria-live="polite" aria-atomic="true">
        {!online && (
          <section className="c-pwa-banner c-pwa-banner--offline" role="status">
            <div>
              <strong>目前處於離線狀態</strong>
              <span>App 可以繼續開啟，但 PTT 資料需要恢復連線後才能更新。</span>
            </div>
          </section>
        )}

        {updateRegistration && (
          <section className="c-pwa-banner c-pwa-banner--update" role="status">
            <div>
              <strong>PTT Alert Hub 有新版本</strong>
              <span>套用更新後會重新載入頁面，不會清除登入狀態。</span>
            </div>
            <div className="c-pwa-banner__actions">
              <button className="c-button c-button--primary c-button--small" type="button" onClick={applyUpdate}>立即更新</button>
              <button className="c-button c-button--secondary c-button--small" type="button" onClick={() => setUpdateRegistration(null)}>稍後</button>
            </div>
          </section>
        )}

        {showInstallBanner && (
          <section className="c-pwa-banner c-pwa-banner--install" role="status">
            <div>
              <strong>安裝 PTT Alert Hub</strong>
              <span>{ios ? '加入 iPhone 主畫面後，可用獨立 App 模式開啟。' : '安裝到裝置後，可從主畫面或應用程式列表直接開啟。'}</span>
            </div>
            <div className="c-pwa-banner__actions">
              <button className="c-button c-button--primary c-button--small" type="button" onClick={() => void handleInstall()}>{ios ? '查看安裝方式' : '安裝 App'}</button>
              <button className="c-button c-button--secondary c-button--small" type="button" onClick={dismissInstall}>稍後</button>
            </div>
          </section>
        )}
      </div>

      {showIosGuide && (
        <div className="c-pwa-dialog-backdrop" role="presentation" onMouseDown={() => setShowIosGuide(false)}>
          <section className="c-pwa-dialog" role="dialog" aria-modal="true" aria-labelledby="pwa-ios-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="c-pwa-dialog__icon">P</div>
            <span className="c-pwa-dialog__eyebrow">iPhone / iPad</span>
            <h2 id="pwa-ios-title">加入主畫面</h2>
            <ol>
              <li>使用 Safari 開啟 PTT Alert Hub。</li>
              <li>點擊 Safari 工具列的「分享」按鈕。</li>
              <li>選擇「加入主畫面」，再點擊右上角的「新增」。</li>
              <li>從主畫面開啟 PTT Alert Hub，即會進入獨立 App 模式。</li>
            </ol>
            <button className="c-button c-button--primary c-button--full" type="button" onClick={() => setShowIosGuide(false)}>我知道了</button>
          </section>
        </div>
      )}
    </>
  );
}
