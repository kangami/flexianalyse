import React from 'react';

interface StatusIndicatorProps {
  status: string;
  isVisible: boolean;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status, isVisible }) => {
  if (!isVisible || !status) return null;

  return (
    <div className="flex justify-start mt-2 mb-2 px-2">
      <span className="text-sm font-medium status-gradient-text">
        {status}
      </span>
    </div>
  );
};

export default StatusIndicator;

