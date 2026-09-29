/**
 * Reusable Select Primitive
 */

import React, { useId } from 'react';

export function Select({
  label,
  options = [],
  value,
  onChange,
  className = '',
  disabled = false,
  id,
  ...props
}) {
  const generatedId = useId();
  const selectId = id || generatedId;

  return (
    <div className={`form-group ${className}`}>
      {label && <label htmlFor={selectId} className="form-label">{label}</label>}
      <select
        id={selectId}
        className="select-control"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value ?? opt.id} value={opt.value ?? opt.id}>
            {opt.label ?? opt.name}
          </option>
        ))}
      </select>
    </div>
  );
}
