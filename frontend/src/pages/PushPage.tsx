import { useEffect, useMemo, useState } from 'react';

import { api } from '../api/client';
import { Feedback, LoadingState } from '../components/Feedback';
import { PageHeader } from '../components/PageHeader';
import type { PushDevice, PushStatus } from '../types';
import { formatDateTime, getErrorMessage } from '../utils';

type NavigatorWithStandalone = Navigator & { standalone?: boolean };

function isIosDevice(): boolean {
  return (
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  );
}

function isStandaloneMode(): boolean {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    (navigator as NavigatorWithStandalone).standalone === true
  );
}

function supportsWebPush(): boolean {
  return (
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
}

function urlBase64ToUint8Array(value: string): Uint8Array {
  const padding = '='.repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = window.atob(base64);
  return Uint8Array.from(raw, (character) => character.charCodeAt(0));
}

function getDeviceName(): string {
  const userAgent = navigator.userAgent;
  if (isIosDevice()) {
    return /ipad/i.test(userAgent) || navigator.maxTouchPoints > 1 ? 'iPad' : 'iPhone';
  }
  if (/android/i.test(userAgent)) {
    return 'Android 裝置';
  }
  if (/windows/i.test(userAgent)) {
    return 'Windows 瀏覽器';
  }
  if (/macintosh|mac os x/i.test(userAgent)) {
    return 'Mac 瀏覽器';
  }
  return '瀏覽器裝置';
}

export function PushPage() {
  const [status, setStatus] = useState<PushStatus | null>(null);
  const [devices, setDevices] = useState<PushDevice[]>([]);
  const [browserSubscription, setBrowserSubscription] = useState<PushSubscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
  } | null>(null);

  const supported = useMemo(supportsWebPush, []);
  const ios = useMemo(isIosDevice, []);
  const standalone = useMemo(isStandaloneMode, []);
  const permission = 'Notification' in window ? Notification.permission : 'default';

  const loadData = async () => {
    setLoading(true);
    try {
      const [nextStatus, nextDevices] = await Promise.all([
        api.getPushStatus(),
        api.getPushSubscriptions(),
      ]);
      setStatus(nextStatus);
      setDevices(nextDevices);

      if (supported) {
        const registration = await navigator.serviceWorker.getRegistration('/');
        const subscription = await registration?.pushManager.getSubscription();
        setBrowserSubscription(subscription ?? null);
      }
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const enablePush = async () => {
    setWorking(true);
    setFeedback(null);
    try {
      if (!supported) {
        throw new Error('目前瀏覽器不支援標準 Web Push。');
      }
      if (ios && !standalone) {
        throw new Error('iPhone／iPad 必須先用 Safari 將網站加入主畫面，再從主畫面開啟。');
      }
      if (!status?.configured || !status.public_key) {
        throw new Error('伺服器尚未完成 VAPID 金鑰設定。');
      }

      const nextPermission = await Notification.requestPermission();
      if (nextPermission !== 'granted') {
        throw new Error('通知權限未允許，請到系統設定中開啟 PTT Alert Hub 通知。');
      }

      const registration =
        (await navigator.serviceWorker.getRegistration('/')) ??
        (await navigator.serviceWorker.register('/sw.js', { scope: '/' }));
      await navigator.serviceWorker.ready;

      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(status.public_key),
        });
      }

      const serialized = subscription.toJSON();
      if (!serialized.endpoint || !serialized.keys?.p256dh || !serialized.keys.auth) {
        throw new Error('瀏覽器沒有回傳完整的 Push Subscription。');
      }

      await api.savePushSubscription({
        endpoint: serialized.endpoint,
        keys: {
          p256dh: serialized.keys.p256dh,
          auth: serialized.keys.auth,
        },
        device_name: getDeviceName(),
        user_agent: navigator.userAgent,
      });

      setBrowserSubscription(subscription);
      setFeedback({ type: 'success', message: '這台裝置已啟用 PWA 推播。' });
      await loadData();
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setWorking(false);
    }
  };

  const disablePush = async () => {
    setWorking(true);
    setFeedback(null);
    try {
      const registration = await navigator.serviceWorker.getRegistration('/');
      const subscription =
        browserSubscription ?? (await registration?.pushManager.getSubscription()) ?? null;

      if (subscription) {
        await api.removePushSubscription(subscription.endpoint);
        await subscription.unsubscribe();
      }

      setBrowserSubscription(null);
      setFeedback({ type: 'success', message: '這台裝置已停止接收推播。' });
      await loadData();
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setWorking(false);
    }
  };

  const testPush = async () => {
    setWorking(true);
    setFeedback(null);
    try {
      const result = await api.testPushNotification();
      setFeedback({ type: 'success', message: result.message });
      await loadData();
    } catch (error) {
      setFeedback({ type: 'error', message: getErrorMessage(error) });
    } finally {
      setWorking(false);
    }
  };

  if (loading) {
    return <LoadingState />;
  }

  const currentEnabled = Boolean(browserSubscription);

  return (
    <div className="p-push">
      <PageHeader
        eyebrow="WEB PUSH"
        title="推播通知"
        description="將這台裝置連結到你的帳號，規則命中新文章時即可收到系統通知。"
        actions={
          currentEnabled ? (
            <button
              className="c-button c-button--danger-ghost"
              type="button"
              disabled={working}
              onClick={() => void disablePush()}
            >
              停用這台裝置
            </button>
          ) : (
            <button
              className="c-button c-button--primary"
              type="button"
              disabled={working || !status?.configured}
              onClick={() => void enablePush()}
            >
              {working ? '處理中…' : '啟用這台裝置'}
            </button>
          )
        }
      />

      {feedback && <Feedback type={feedback.type} message={feedback.message} />}
      {!status?.configured && (
        <Feedback
          type="info"
          message="系統尚未設定 VAPID 金鑰。管理員完成 Backend 與 Worker 環境變數後才能啟用推播。"
        />
      )}
      {ios && !standalone && (
        <Feedback
          type="info"
          message="iPhone／iPad 必須先使用 Safari 加入主畫面，再從主畫面開啟 PTT Alert Hub，才能要求通知權限。"
        />
      )}

      <section className="p-push__status-grid" aria-label="推播狀態">
        <article className="c-stat-card">
          <span className="c-stat-card__label">瀏覽器支援</span>
          <strong className="c-stat-card__value c-stat-card__value--date">
            {supported ? '支援 Web Push' : '不支援'}
          </strong>
          <small className="c-stat-card__meta">Service Worker、Push API 與 Notification API</small>
        </article>
        <article className="c-stat-card">
          <span className="c-stat-card__label">通知權限</span>
          <strong className="c-stat-card__value c-stat-card__value--date">
            {permission === 'granted' ? '已允許' : permission === 'denied' ? '已拒絕' : '尚未詢問'}
          </strong>
          <small className="c-stat-card__meta">權限只會在你點擊啟用時提出</small>
        </article>
        <article className="c-stat-card">
          <span className="c-stat-card__label">目前裝置</span>
          <strong className="c-stat-card__value c-stat-card__value--date">
            {currentEnabled ? '已啟用' : '未啟用'}
          </strong>
          <small className="c-stat-card__meta">{getDeviceName()}</small>
        </article>
        <article className="c-stat-card">
          <span className="c-stat-card__label">帳號裝置數</span>
          <strong className="c-stat-card__value">{status?.enabled_subscription_count ?? 0}</strong>
          <small className="c-stat-card__meta">可同時使用手機、桌機與筆電</small>
        </article>
      </section>

      <section className="c-card p-push__test-card">
        <div>
          <span className="c-card__eyebrow">DELIVERY TEST</span>
          <h2 className="c-card__title">測試推播</h2>
          <p>測試會傳送到這個帳號目前所有啟用裝置。</p>
        </div>
        <button
          className="c-button c-button--secondary"
          type="button"
          disabled={working || (status?.enabled_subscription_count ?? 0) === 0}
          onClick={() => void testPush()}
        >
          發送測試通知
        </button>
      </section>

      <section className="c-card c-table-card">
        <div className="c-card__header p-push__device-header">
          <div>
            <span className="c-card__eyebrow">DEVICES</span>
            <h2 className="c-card__title">已連結裝置</h2>
          </div>
          <button
            className="c-button c-button--secondary c-button--small"
            type="button"
            onClick={() => void loadData()}
          >
            重新整理
          </button>
        </div>
        <div className="c-table-wrap">
          <table className="c-table">
            <thead>
              <tr>
                <th>裝置</th>
                <th>狀態</th>
                <th>建立時間</th>
                <th>最近成功</th>
                <th>失敗次數</th>
              </tr>
            </thead>
            <tbody>
              {devices.map((device) => (
                <tr key={device.id}>
                  <td>{device.device_name}</td>
                  <td>{device.enabled ? '啟用' : '已停用'}</td>
                  <td>{formatDateTime(device.created_at)}</td>
                  <td>{formatDateTime(device.last_success_at)}</td>
                  <td>{device.failure_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {devices.length === 0 && <div className="c-empty-state">尚未連結任何推播裝置。</div>}
      </section>
    </div>
  );
}
