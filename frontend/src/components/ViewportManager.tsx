import { useEffect } from 'react';

const KEYBOARD_HEIGHT_THRESHOLD = 120;
const RESTORE_DELAYS = [0, 80, 320];

function isEditableElement(element: Element | null): boolean {
  return (
    element instanceof HTMLInputElement ||
    element instanceof HTMLTextAreaElement ||
    element instanceof HTMLSelectElement ||
    (element instanceof HTMLElement && element.isContentEditable)
  );
}

export function ViewportManager() {
  useEffect(() => {
    const root = document.documentElement;
    const viewport = window.visualViewport;
    let maximumViewportHeight = Math.max(window.innerHeight, viewport?.height ?? 0);
    const restoreTimers = new Set<number>();

    const applyViewport = () => {
      const visibleHeight = Math.max(1, Math.round(viewport?.height ?? window.innerHeight));
      const offsetTop = Math.max(0, Math.round(viewport?.offsetTop ?? 0));
      const inputFocused = isEditableElement(document.activeElement);

      if (!inputFocused && visibleHeight > maximumViewportHeight - KEYBOARD_HEIGHT_THRESHOLD) {
        maximumViewportHeight = Math.max(maximumViewportHeight, visibleHeight, window.innerHeight);
      }

      const keyboardOpen =
        inputFocused && maximumViewportHeight - visibleHeight >= KEYBOARD_HEIGHT_THRESHOLD;

      root.style.setProperty('--app-viewport-height', `${visibleHeight}px`);
      root.style.setProperty(
        '--app-viewport-offset-top',
        `${keyboardOpen ? offsetTop : 0}px`,
      );
      root.classList.toggle('is-virtual-keyboard-open', keyboardOpen);
    };

    const resetDocumentOffset = () => {
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      applyViewport();
    };

    const scheduleRestore = () => {
      for (const delay of RESTORE_DELAYS) {
        const timer = window.setTimeout(() => {
          restoreTimers.delete(timer);
          resetDocumentOffset();
        }, delay);
        restoreTimers.add(timer);
      }
    };

    const handleOrientationChange = () => {
      maximumViewportHeight = 0;
      scheduleRestore();
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        scheduleRestore();
      }
    };

    applyViewport();
    viewport?.addEventListener('resize', applyViewport);
    viewport?.addEventListener('scroll', applyViewport);
    window.addEventListener('resize', applyViewport);
    window.addEventListener('orientationchange', handleOrientationChange);
    window.addEventListener('pageshow', scheduleRestore);
    document.addEventListener('focusin', applyViewport);
    document.addEventListener('focusout', scheduleRestore);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      viewport?.removeEventListener('resize', applyViewport);
      viewport?.removeEventListener('scroll', applyViewport);
      window.removeEventListener('resize', applyViewport);
      window.removeEventListener('orientationchange', handleOrientationChange);
      window.removeEventListener('pageshow', scheduleRestore);
      document.removeEventListener('focusin', applyViewport);
      document.removeEventListener('focusout', scheduleRestore);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      for (const timer of restoreTimers) window.clearTimeout(timer);
      root.classList.remove('is-virtual-keyboard-open');
      root.style.removeProperty('--app-viewport-height');
      root.style.removeProperty('--app-viewport-offset-top');
    };
  }, []);

  return null;
}
