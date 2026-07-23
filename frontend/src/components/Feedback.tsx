interface FeedbackProps {
  type: 'success' | 'error' | 'info';
  message: string;
}

export function Feedback({ type, message }: FeedbackProps) {
  return <div className={`c-feedback c-feedback--${type}`}>{message}</div>;
}

export function LoadingState() {
  return <div className="c-loading">資料載入中…</div>;
}

export function EmptyState({ message }: { message: string }) {
  return <div className="c-empty-state">{message}</div>;
}
