/**
 * Global Error State Component
 * Formatted as an authoritative operational bulletin with actionable retry.
 */

import React from 'react';
import { AlertTriangleIcon, RefreshCwIcon } from '../icons/Icons.jsx';
import { Button } from '../ui/Button.jsx';

export function ErrorState({
  title = 'Forecast Verification Feed Unavailable',
  message = 'Failed to retrieve grid-level forecast verification metrics. The Phase 0/FastAPI pipeline may be initializing.',
  onRetry = null,
  className = '',
}) {
  return (
    <div
      className={`error-container ${className}`}
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
      role="alert"
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '42px',
          height: '42px',
          borderRadius: '50%',
          backgroundColor: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.35)',
        }}
      >
        <AlertTriangleIcon size={20} style={{ color: '#F87171' }} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
          {title}
        </h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          {message}
        </p>
      </div>

      {onRetry && (
        <Button
          size="sm"
          variant="secondary"
          onClick={onRetry}
          iconLeft={RefreshCwIcon}
          style={{ marginTop: '4px' }}
        >
          Retry Verification Feed
        </Button>
      )}
    </div>
  );
}
