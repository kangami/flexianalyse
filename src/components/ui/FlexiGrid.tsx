import { useState } from 'react';

export interface FlexiGridColumn<T> {
  key: string;
  header: string;
  render: (
    item: T,
    isEditing: boolean,
    editState: Partial<T>,
    setEditState: (s: Partial<T>) => void
  ) => React.ReactNode;
}

interface FlexiGridProps<T extends { id: string }> {
  columns: FlexiGridColumn<T>[];
  data: T[];
  emptyState?: Partial<T>;
  onCreate: (item: Partial<T>) => Promise<T | null>;
  onUpdate: (id: string, item: Partial<T>) => Promise<T | null>;
  onDelete: (id: string) => Promise<boolean>;
  onBulkDelete?: (ids: string[]) => Promise<boolean>;
  getId?: (item: T) => string;
}

export function FlexiGrid<T extends { id: string }>({
  columns,
  data,
  emptyState = {} as Partial<T>,
  onCreate,
  onUpdate,
  onDelete,
  onBulkDelete,
  getId = (item) => item.id,
}: FlexiGridProps<T>) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editState, setEditState] = useState<Partial<T>>({} as Partial<T>);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isAdding, setIsAdding] = useState(false);

  const allSelected = data.length > 0 && data.every((r) => selectedIds.has(getId(r)));

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(data.map((r) => getId(r))));
    }
  };

  const toggleOne = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  const startEdit = (item: T) => {
    setEditingId(getId(item));
    setEditState({ ...item });
    setIsAdding(false);
  };

  const startAdd = () => {
    setIsAdding(true);
    setEditingId(null);
    setEditState({ ...emptyState });
  };

  const cancel = () => {
    setEditingId(null);
    setIsAdding(false);
    setEditState({} as Partial<T>);
  };

  const saveEdit = async () => {
    if (editingId) {
      const result = await onUpdate(editingId, editState);
      if (result) cancel();
    }
  };

  const saveAdd = async () => {
    const result = await onCreate(editState);
    if (result) cancel();
  };

  const handleDelete = async (id: string) => {
    await onDelete(id);
  };

  const handleBulkDelete = async () => {
    if (onBulkDelete && selectedIds.size > 0) {
      const ids = Array.from(selectedIds);
      const ok = await onBulkDelete(ids);
      if (ok) setSelectedIds(new Set());
    }
  };

  const hasSelection = selectedIds.size > 0;

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <button onClick={startAdd} disabled={isAdding}
          className="text-green-600 hover:text-green-800 disabled:text-gray-300 disabled:cursor-not-allowed" title="Add row">
          <i className="bi bi-plus-lg text-sm"></i>
        </button>
        <button onClick={() => {
          if (selectedIds.size === 1) {
            const item = data.find((r) => getId(r) === Array.from(selectedIds)[0]);
            if (item) startEdit(item);
          }
        }} disabled={selectedIds.size !== 1 || isAdding}
          className="text-blue-500 hover:text-blue-700 disabled:text-gray-300 disabled:cursor-not-allowed" title="Edit selected">
          <i className="bi bi-pencil text-xs"></i>
        </button>
        <button onClick={handleBulkDelete} disabled={!hasSelection || isAdding}
          className="text-red-500 hover:text-red-700 disabled:text-gray-300 disabled:cursor-not-allowed"
          title={hasSelection ? `Delete ${selectedIds.size} selected` : 'Delete selected'}>
          <i className="bi bi-x-lg text-xs"></i>
        </button>
        {hasSelection && (
          <span className="text-[10px] text-gray-400">{selectedIds.size} selected</span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200 text-gray-500">
              <th className="text-left py-1.5 pr-1 w-5">
                <input type="checkbox" className="w-3 h-3" checked={allSelected} onChange={toggleAll} />
              </th>
              {columns.map((col) => (
                <th key={col.key} className="text-left py-1.5 font-medium">{col.header}</th>
              ))}
              <th className="text-right py-1.5 w-8"></th>
            </tr>
          </thead>
          <tbody>
            {isAdding && (
              <tr className="border-b border-gray-100 bg-purple-50">
                <td className="py-1 pr-1"></td>
                {columns.map((col) => (
                  <td key={col.key} className="py-1">
                    {col.render({} as T, true, editState, setEditState)}
                  </td>
                ))}
                <td className="py-1 text-right">
                  <div className="flex gap-1 justify-end">
                    <button onClick={saveAdd} className="text-green-600 hover:text-green-800" title="Save">
                      <i className="bi bi-check-lg"></i>
                    </button>
                    <button onClick={cancel} className="text-gray-400 hover:text-gray-600" title="Cancel">
                      <i className="bi bi-x-lg"></i>
                    </button>
                  </div>
                </td>
              </tr>
            )}
            {data.map((item) => {
              const id = getId(item);
              const isEditing = editingId === id;
              return (
                <tr key={id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-1 pr-1">
                    <input type="checkbox" className="w-3 h-3" checked={selectedIds.has(id)} onChange={() => toggleOne(id)} />
                  </td>
                  {columns.map((col) => (
                    <td key={col.key} className="py-1">
                      {col.render(item, isEditing, editState, setEditState)}
                    </td>
                  ))}
                  <td className="py-1 text-right">
                    {isEditing ? (
                      <div className="flex gap-1 justify-end">
                        <button onClick={saveEdit} className="text-green-600 hover:text-green-800" title="Save">
                          <i className="bi bi-check-lg"></i>
                        </button>
                        <button onClick={cancel} className="text-gray-400 hover:text-gray-600" title="Cancel">
                          <i className="bi bi-x-lg"></i>
                        </button>
                      </div>
                    ) : (
                      <button onClick={() => handleDelete(id)} className="text-red-400 hover:text-red-600 px-1" title="Delete">
                        <i className="bi bi-x-lg"></i>
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}