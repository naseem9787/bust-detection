/**
 * Segmented Control (Pill Switcher)
 * Dense button group for switching mutually exclusive filter views
 */

import React from 'react';

export function SegmentedControl({
  options = [],
  value,
  onChange,
  className = '',
  ariaLabel = 'Segmented options',
}) {
  return (
    <div className={`segmented-control ${className}`} role="group" aria-label={ariaLabel}>
      {options.map((option) => {
        const optValue = option.value ?? option.id;
        const optLabel = option.label ?? option.name;
        const isActive = optValue === value;

        return (
          <button
            key={optValue}
            type="button"
            className={`segmented-btn ${isActive ? 'active' : ''}`}
            onClick={() => onChange(optValue)}
            aria-pressed={isActive}
          >
            {option.icon && (
              <span style={{ marginRight: '4px', verticalAlign: 'middle' }}>
                {option.icon}
              </span>
            )}
            {optLabel}
          </button>
        );
      })}
    </div>
  );
}
