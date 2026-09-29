/**
 * Reusable Card / Panel Primitive
 * Restrained engineering frame without excessive glow or giant rounded corners
 */

import React from 'react';

export function Card({
  title,
  subtitle,
  icon: Icon = null,
  actions = null,
  status = null,
  footer = null,
  noPadding = false,
  className = '',
  children,
  ...props
}) {
  const hasHeader = title || subtitle || Icon || actions || status;

  return (
    <div className={`card-panel ${className}`} {...props}>
      {hasHeader && (
        <div className="card-header">
          <div className="card-title-group">
            {Icon && <Icon size={16} style={{ color: 'var(--text-secondary)' }} />}
            <div>
              {title && <div className="card-title">{title}</div>}
              {subtitle && <div className="card-subtitle">{subtitle}</div>}
            </div>
            {status}
          </div>
          {actions && <div className="card-actions">{actions}</div>}
        </div>
      )}
      <div className={`card-body ${noPadding ? 'no-padding' : ''}`}>
        {children}
      </div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
}
