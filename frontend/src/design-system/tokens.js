/**
 * Foundational Design System Tokens
 * SIH 26079: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts
 *
 * Designed for a professional meteorological intelligence platform (NCMRWF / MoES).
 * Authoritative, restrained, high-density, scientific aesthetic.
 */

export const TOKENS = {
  // Color Palette: Deep Slate / Meteorological Neutral Foundation
  colors: {
    bg: {
      canvas: '#0A0E17',      // Deepest background for app canvas & map underlay
      surface: '#111827',     // Main panel / workbench surface
      elevated: '#1F2937',    // Slightly elevated surface (toolbars, popovers)
      subtle: '#1E293B',      // Secondary subtle background (table rows, inputs)
      hover: '#26334D',       // Interactive element hover
      active: '#334155',      // Interactive element active state
    },
    border: {
      subtle: '#1F2937',      // Barely visible divider
      default: '#2E3A52',     // Standard panel and card borders
      strong: '#475569',      // Input borders, focused outlines
      focus: '#38BDF8',       // Focus ring color
    },
    text: {
      primary: '#F9FAFB',     // High-contrast primary reading text
      secondary: '#94A3B8',   // Medium-contrast metadata, units, labels
      muted: '#64748B',       // Low-contrast timestamps, placeholders
      inverse: '#0A0E17',     // Text on bright badges / primary buttons
    },
    // Meteorological Bust Risk Tiers (Aligned with IMD operational severity colors)
    risk: {
      low: {
        label: 'Low Risk',
        color: '#10B981',     // Green
        bg: 'rgba(16, 185, 129, 0.12)',
        border: 'rgba(16, 185, 129, 0.35)',
        text: '#34D399',
      },
      moderate: {
        label: 'Moderate',
        color: '#F59E0B',     // Amber / Yellow
        bg: 'rgba(245, 158, 11, 0.12)',
        border: 'rgba(245, 158, 11, 0.35)',
        text: '#FBBF24',
      },
      elevated: {
        label: 'Elevated',
        color: '#F97316',     // Orange
        bg: 'rgba(249, 115, 22, 0.12)',
        border: 'rgba(249, 115, 22, 0.35)',
        text: '#FB923C',
      },
      high: {
        label: 'High Risk',
        color: '#EF4444',     // Red
        bg: 'rgba(239, 68, 68, 0.12)',
        border: 'rgba(239, 68, 68, 0.35)',
        text: '#F87171',
      },
      extreme: {
        label: 'Severe / Bust',
        color: '#B91C1C',     // Dark Red / Maroon
        bg: 'rgba(185, 28, 28, 0.20)',
        border: 'rgba(185, 28, 28, 0.50)',
        text: '#FCA5A5',
      },
    },
    // Calibrated Forecast Confidence Tiers
    confidence: {
      high: {
        label: 'High Confidence',
        range: '≥ 80%',
        color: '#10B981',
        bg: 'rgba(16, 185, 129, 0.12)',
        border: 'rgba(16, 185, 129, 0.35)',
        text: '#34D399',
      },
      moderate: {
        label: 'Moderate Confidence',
        range: '50% – 79%',
        color: '#F59E0B',
        bg: 'rgba(245, 158, 11, 0.12)',
        border: 'rgba(245, 158, 11, 0.35)',
        text: '#FBBF24',
      },
      low: {
        label: 'Low / Uncertain',
        range: '< 50%',
        color: '#F43F5E',
        bg: 'rgba(244, 63, 94, 0.12)',
        border: 'rgba(244, 63, 94, 0.35)',
        text: '#FDA4AF',
      },
    },
    // Weather Variable Palette
    variables: {
      precip: {
        name: 'Precipitation',
        unit: 'mm',
        color: '#0284C7',
        accent: '#38BDF8',
      },
      temp: {
        name: '2m Temperature',
        unit: '°C',
        color: '#EA580C',
        accent: '#FB923C',
      },
      mslp: {
        name: 'Mean Sea Level Pressure',
        unit: 'hPa',
        color: '#6366F1',
        accent: '#818CF8',
      },
    },
  },

  // Typography Tokens
  typography: {
    fontFamily: {
      sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      mono: "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace",
    },
    fontSize: {
      xs: '0.6875rem',    // 11px - dense captions, coordinate stamps, axis ticks
      sm: '0.75rem',      // 12px - secondary labels, table headers, metadata
      base: '0.8125rem',  // 13px - default body text, input controls
      md: '0.875rem',     // 14px - card titles, section headings
      lg: '1.0625rem',    // 17px - prominent panel headers, key callouts
      xl: '1.375rem',     // 22px - major stat values
      '2xl': '1.75rem',   // 28px - primary overview metric
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.2,
      snug: 1.35,
      normal: 1.5,
    },
  },

  // Spacing Scale (4px baseline grid)
  spacing: {
    1: '0.25rem',   // 4px
    2: '0.5rem',    // 8px
    3: '0.75rem',   // 12px
    4: '1rem',      // 16px
    5: '1.25rem',   // 20px
    6: '1.5rem',    // 24px
    8: '2rem',      // 32px
    10: '2.5rem',   // 40px
    12: '3rem',     // 48px
  },

  // Restrained Radii (No giant pill cards)
  radius: {
    none: '0px',
    sm: '3px',
    md: '5px',
    lg: '6px',
    full: '9999px', // only for status pills & badges
  },

  // Subtle, scientific shadows
  shadows: {
    subtle: '0 1px 2px 0 rgba(0, 0, 0, 0.4)',
    elevated: '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3)',
    panel: '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -4px rgba(0, 0, 0, 0.3)',
  },

  // Standard z-index layers
  zIndex: {
    canvas: 0,
    surface: 10,
    header: 40,
    popover: 50,
    modal: 100,
    tooltip: 200,
  },
};
