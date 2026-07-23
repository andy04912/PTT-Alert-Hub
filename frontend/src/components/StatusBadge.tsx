import type { CrawlRunStatus } from '../types';

interface StatusBadgeProps {
  status: CrawlRunStatus;
}

const statusLabel: Record<CrawlRunStatus, string> = {
  running: '執行中',
  success: '成功',
  failed: '失敗',
  skipped: '略過',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`c-status c-status--${status}`}>{statusLabel[status]}</span>;
}
