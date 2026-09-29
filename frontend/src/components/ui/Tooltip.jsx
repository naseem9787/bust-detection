/**
 * Restrained Data Tooltip Primitive
 */

import React, { useState } from 'react';

export function Tooltip({ content, children, className = '' }) {
  const [visible, setVisible] = useState(false);

  return (
    <span
      className={`tooltip-wrapper ${className}`}
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && content && (
        <span
          role="tooltip"
          style={{
            position: 'absolute',
            bottom: 'calc(100% + 6px)',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: '#1F2937',
            color: '#F9FAFB',
            padding: '4px 8px',
            borderRadius: '4px',
            maxWidth: '280px',
            width: 'max-content',
            whiteSpace: 'normal',
            lineHeight: 1.4,
            textAlign: 'left',
            boxShadow: 'var(--shadow-md)',
            border: '1px solid var(--border-default)',
            zIndex: 200,
            pointerEvents: 'none',
          }}
        >
          {content}
        </span>
      )}
    </span>
  );
}
