import React, { useEffect } from 'react';
import { getCalApi } from '@calcom/embed-react';

// The Cal.com event link, e.g. "flexianalyse/demo". Set VITE_CAL_LINK to your
// real event; Cal.com handles slots, timezones, the Zoom link and confirmations.
const CAL_LINK = import.meta.env.VITE_CAL_LINK || 'flexianalyse/demo';

interface BookDemoButtonProps {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

const BookDemoButton: React.FC<BookDemoButtonProps> = ({ className, style, children }) => {
  useEffect(() => {
    getCalApi().then((cal) => {
      cal('ui', { hideEventTypeDetails: false, layout: 'month_view' });
    });
  }, []);

  return (
    <button
      type="button"
      data-cal-link={CAL_LINK}
      data-cal-config='{"layout":"month_view"}'
      className={className}
      style={style}
    >
      {children ?? 'Book a Demo'}
    </button>
  );
};

export default BookDemoButton;
