import { useEffect, useRef, useState } from 'react';

import { api } from '../api/client';
import type { BoardCategory, BoardDirectoryEntry, BoardOption } from '../types';
import { getErrorMessage } from '../utils';

interface BoardPickerProps {
  value: string;
  onChange: (board: string) => void;
  disabled?: boolean;
}

interface CategoryHistoryItem {
  id: number;
  title: string;
}

export function BoardPicker({ value, onChange, disabled = false }: BoardPickerProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<BoardOption[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [browserOpen, setBrowserOpen] = useState(false);
  const [browserLoading, setBrowserLoading] = useState(false);
  const [category, setCategory] = useState<BoardCategory | null>(null);
  const [categoryHistory, setCategoryHistory] = useState<CategoryHistoryItem[]>([]);
  const [browserError, setBrowserError] = useState<string | null>(null);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, []);

  useEffect(() => {
    if (!open || disabled) {
      return;
    }

    let active = true;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setSearchError(null);
      try {
        const result = await api.searchBoards(value.trim(), 30);
        if (active) {
          setSuggestions(result);
        }
      } catch (error) {
        if (active) {
          setSearchError(getErrorMessage(error));
          setSuggestions([]);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }, value.trim() ? 320 : 0);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [disabled, open, value]);

  const revealPickerOnMobile = () => {
    setOpen(true);

    if (!window.matchMedia('(max-width: 640px)').matches) {
      return;
    }

    // 等待手機鍵盤完成展開，再把輸入區移到畫面上方，保留結果清單的可視空間。
    window.setTimeout(() => {
      rootRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 220);
  };

  const selectBoard = (board: string) => {
    onChange(board);
    setOpen(false);
    setBrowserOpen(false);
  };

  const loadCategory = async (
    categoryId: number,
    history: CategoryHistoryItem[],
  ) => {
    setBrowserLoading(true);
    setBrowserError(null);
    try {
      const result = await api.getBoardCategory(categoryId);
      setCategory(result);
      setCategoryHistory(history);
    } catch (error) {
      setBrowserError(getErrorMessage(error));
    } finally {
      setBrowserLoading(false);
    }
  };

  const toggleBrowser = () => {
    const nextOpen = !browserOpen;
    setBrowserOpen(nextOpen);
    setOpen(false);

    if (nextOpen && !category) {
      void loadCategory(1, [{ id: 1, title: 'PTT 分類看板' }]);
    }
  };

  const enterCategory = (entry: BoardDirectoryEntry) => {
    if (entry.category_id === null) {
      return;
    }

    void loadCategory(entry.category_id, [
      ...categoryHistory,
      { id: entry.category_id, title: entry.name },
    ]);
  };

  const goBackCategory = () => {
    if (categoryHistory.length <= 1) {
      return;
    }

    const previousHistory = categoryHistory.slice(0, -1);
    const previous = previousHistory.at(-1);
    if (previous) {
      void loadCategory(previous.id, previousHistory);
    }
  };

  const resultLabel = value.trim() ? '搜尋結果' : '目前熱門看板';

  return (
    <div className="c-board-picker" ref={rootRef}>
      <div className="c-board-picker__control">
        <div className="c-board-picker__search">
          <input
            className="c-input c-board-picker__input"
            placeholder="搜尋中文板名或看板代號"
            value={value}
            disabled={disabled}
            autoComplete="off"
            required
            role="combobox"
            aria-expanded={open}
            aria-controls="board-picker-results"
            onFocus={revealPickerOnMobile}
            onChange={(event) => {
              onChange(event.target.value);
              setOpen(true);
            }}
          />

          {open && (
            <div className="c-board-picker__popover" id="board-picker-results">
              <div className="c-board-picker__popover-header">
                <strong>{resultLabel}</strong>
                <small>{loading ? '讀取中…' : `${suggestions.length} 個結果`}</small>
              </div>

              {searchError ? (
                <p className="c-board-picker__message c-board-picker__message--error">
                  {searchError}
                </p>
              ) : suggestions.length > 0 ? (
                <div className="c-board-picker__results" role="listbox">
                  {suggestions.map((option) => (
                    <button
                      className="c-board-option"
                      type="button"
                      role="option"
                      aria-selected={value === option.board}
                      key={option.board}
                      onClick={() => selectBoard(option.board)}
                    >
                      <span className="c-board-option__main">
                        <strong className="c-board-option__name">{option.board}</strong>
                        <span className="c-board-option__title">
                          {option.title || 'PTT 看板'}
                        </span>
                      </span>
                      <span className="c-board-option__meta">
                        {option.category || '未分類'}
                        {option.popularity !== null ? `・${option.popularity} 人` : ''}
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="c-board-picker__message">
                  找不到建議項目。仍可保留目前輸入值，建立規則時會連線 PTT 驗證。
                </p>
              )}
            </div>
          )}
        </div>

        <button
          className="c-button c-button--secondary"
          type="button"
          disabled={disabled}
          aria-expanded={browserOpen}
          onClick={toggleBrowser}
        >
          {browserOpen ? '關閉分類' : '瀏覽分類'}
        </button>
      </div>

      {browserOpen && (
        <div className="c-board-browser">
          <div className="c-board-browser__header">
            <div>
              <span className="c-board-browser__eyebrow">PTT DIRECTORY</span>
              <strong className="c-board-browser__title">
                {categoryHistory.at(-1)?.title ?? 'PTT 分類看板'}
              </strong>
            </div>
            <button
              className="c-button c-button--ghost c-button--small"
              type="button"
              disabled={categoryHistory.length <= 1 || browserLoading}
              onClick={goBackCategory}
            >
              返回上層
            </button>
          </div>

          <div className="c-board-browser__breadcrumb" aria-label="看板分類路徑">
            {categoryHistory.map((item, index) => (
              <span key={`${item.id}-${index}`}>
                {index > 0 && <span aria-hidden="true">/</span>}
                {item.title}
              </span>
            ))}
          </div>

          {browserError ? (
            <p className="c-board-picker__message c-board-picker__message--error">
              {browserError}
            </p>
          ) : browserLoading ? (
            <p className="c-board-picker__message">正在讀取 PTT 分類目錄…</p>
          ) : category && category.entries.length > 0 ? (
            <div className="c-board-browser__list">
              {category.entries.map((entry) => (
                <button
                  className={`c-directory-entry c-directory-entry--${entry.kind}`}
                  type="button"
                  key={`${entry.kind}-${entry.board ?? entry.category_id}`}
                  onClick={() =>
                    entry.kind === 'board' && entry.board
                      ? selectBoard(entry.board)
                      : enterCategory(entry)
                  }
                >
                  <span className="c-directory-entry__icon" aria-hidden="true">
                    {entry.kind === 'category' ? '›' : '#'}
                  </span>
                  <span className="c-directory-entry__content">
                    <strong>{entry.name}</strong>
                    <small>{entry.description || entry.category || 'PTT 看板'}</small>
                  </span>
                  {entry.kind === 'board' && entry.popularity !== null && (
                    <span className="c-directory-entry__count">{entry.popularity}</span>
                  )}
                </button>
              ))}
            </div>
          ) : (
            <p className="c-board-picker__message">這個分類目前沒有可顯示的項目。</p>
          )}
        </div>
      )}
    </div>
  );
}
