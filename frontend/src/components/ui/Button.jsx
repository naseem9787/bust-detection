/**
 * Reusable Button Primitive
 * Variants: primary, secondary, outline, ghost, danger
 * Sizes: sm (28px), md (34px)
 */

import React from 'react';

export function Button({
  children,
  variant = 'secondary',
  size = 'md',
  iconLeft: IconLeft = null,
  iconRight: IconRight = null,
  disabled = false,
  className = '',
  type = 'button',
  onClick,
  ...props
}) {
  const classes = [
    'btn',
    `btn-${variant}`,
    `btn-${size}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <button
      type={type}
      className={classes}
      disabled={disabled}
      onClick={onClick}
      {...props}
    >
      {IconLeft && <IconLeft size={size === 'sm' ? 14 : 16} />}
      {children}
      {IconRight && <IconRight size={size === 'sm' ? 14 : 16} />}
    </button>
  );
}
