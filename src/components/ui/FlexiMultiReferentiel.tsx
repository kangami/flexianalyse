import React, { useState, useRef, useEffect } from 'react';
import { X, ChevronDown } from 'lucide-react';

interface FlexiMultiReferentielProps {
  label?: string;
  availableItems: string[];
  selectedItems: string[];
  onItemSelect: (item: string) => void;
  onItemRemove: (item: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export function FlexiMultiReferentiel({
  label,
  availableItems,
  selectedItems,
  onItemSelect,
  onItemRemove,
  disabled = false,
  placeholder = '— Select items —',
  className = '',
}: FlexiMultiReferentielProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter out already selected items from available items
  const filteredItems = availableItems.filter(item => !selectedItems.includes(item));

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {label && (
        <label className="text-[10px] font-semibold text-gray-500 uppercase block mb-1">
          {label}
        </label>
      )}
      
      <div className="border border-gray-300 rounded-md bg-white overflow-hidden">
        {/* Selected Items Display */}
        <div className="flex flex-wrap gap-1 px-1.5 py-1 min-h-[30px] items-center">
          {selectedItems.length > 0 ? (
            selectedItems.map(item => (
              <div
                key={item}
                className="bg-purple-100 text-purple-700 text-xs px-2 py-1 rounded-md flex items-center gap-1 font-medium"
              >
                {item}
                <button
                  onClick={() => onItemRemove(item)}
                  disabled={disabled}
                  className="hover:text-purple-900 disabled:opacity-50 transition-colors"
                  title="Remove"
                >
                  <X size={14} />
                </button>
              </div>
            ))
          ) : (
            <span className="text-xs text-gray-400">{placeholder}</span>
          )}
          
          {/* Dropdown Toggle Button */}
          <button
            onClick={() => !disabled && setIsOpen(!isOpen)}
            disabled={disabled}
            className="ml-auto p-1 hover:bg-gray-100 disabled:opacity-50 transition-colors"
            title="Toggle dropdown"
          >
            <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
          </button>
        </div>

        {/* Dropdown Menu */}
        {isOpen && !disabled && (
          <div className="border-t border-gray-200 bg-white max-h-48 overflow-y-auto">
            {filteredItems.length > 0 ? (
              filteredItems.map(item => (
                <button
                  key={item}
                  onClick={() => {
                    onItemSelect(item);
                    setIsOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 text-xs hover:bg-purple-50 hover:text-purple-700 transition-colors font-medium"
                >
                  {item}
                </button>
              ))
            ) : (
              <div className="px-3 py-2 text-xs text-gray-400">All items selected</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
