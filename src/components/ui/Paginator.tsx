import { useState } from 'react';

interface PaginatorProps<T> {
  items: T[];
  pageSize?: number;
  children: (pageItems: T[]) => React.ReactNode;
}

export function Paginator<T>({ items, pageSize = 5, children }: PaginatorProps<T>) {
  const [page, setPage] = useState(0);
  const totalPages = Math.ceil(items.length / pageSize);
  const pageItems = items.slice(page * pageSize, page * pageSize + pageSize);

  return (
    <>
      {children(pageItems)}
      {items.length > pageSize && (
        <div className="flex items-center justify-between mt-2">
          <button
            disabled={page === 0}
            onClick={() => setPage(p => p - 1)}
            className="text-purple-600 disabled:text-gray-300 disabled:cursor-not-allowed hover:text-purple-800 transition-colors"
          >
            <i className="bi bi-chevron-left text-xs"></i>
          </button>
          <span className="text-[10px] text-gray-500">{page + 1} / {totalPages}</span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => setPage(p => p + 1)}
            className="text-purple-600 disabled:text-gray-300 disabled:cursor-not-allowed hover:text-purple-800 transition-colors"
          >
            <i className="bi bi-chevron-right text-xs"></i>
          </button>
        </div>
      )}
    </>
  );
}
