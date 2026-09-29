/**
 * Reusable Badge Primitive
 */

import React from 'react';

export function Badge({
  children,
  variant = 'neutral',
  dot = false,
  className = '',
  ...props
}) {
  return (
    <span className={`badge badge-${variant} ${className}`} {...props}>
      {dot && <span className="badge-dot" />}
      {children}
    </span>
  );
}
