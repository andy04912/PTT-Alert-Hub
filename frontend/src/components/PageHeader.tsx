import type { ReactNode } from 'react';

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <header className="c-page-header">
      <div>
        {eyebrow && <span className="c-page-header__eyebrow">{eyebrow}</span>}
        <h1 className="c-page-header__title">{title}</h1>
        <p className="c-page-header__description">{description}</p>
      </div>
      {actions && <div className="c-page-header__actions">{actions}</div>}
    </header>
  );
}
