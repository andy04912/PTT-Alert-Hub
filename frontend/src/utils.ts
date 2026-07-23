export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }

  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  const normalizedValue = hasTimezone ? value : `${value}Z`;
  const date = new Date(normalizedValue);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date);
}

export function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '發生未知錯誤';
}
