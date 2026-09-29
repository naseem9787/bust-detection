/**
 * EmptyState Component
 * SIH 26079: AI-Based Forecast Bust Detection Platform
 *
 * Professional, restrained empty state notification for missing queries,
 * unpopulated regions, or filtered archives.
 */

import React from 'react';
import { DatabaseIcon, RefreshCwIcon } from '../icons/Icons.jsx';
import { Button } from '../ui/Button.jsx';

export function EmptyState({
  title = 'No Meteorological Verification Data Found',
  message = 'No verification records match the selected parameters or lead-time criteria. Try selecting an alternate cycle or region.',
  onAction = null,
  actionLabel = 'Reset Parameters',
  className = '',
}) {
  return (
    <div
      className={`empty-state-card ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 24px',
        textAlign: 'center',
        gap: '14px',
        maxWidth: '540px',
        margin: '32px auto',
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-sm)',
      }}
      role="status"
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '42px',
          height: '42px',
          borderRadius: '50%',
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          border: '1px solid rgba(56, 189, 248, 0.3)',
        }}
      >
        <DatabaseIcon size={20} style={{ color: '#38BDF8' }} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
          {title}
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          {message}
        </p>
      </div>

      {onAction && (
        <Button variant="secondary" size="sm" onClick={onAction}>
          <RefreshCwIcon size={13} style={{ marginRight: '6px' }} />
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
