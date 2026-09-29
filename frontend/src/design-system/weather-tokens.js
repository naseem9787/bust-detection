/**
 * Meteorological Domain Constants & Definitions
 * Directly aligned with src/config.py and src/regions.py
 */

export const LEAD_DAYS = [
  { day: 1, hours: 24, label: 'Day 1 (+24h)' },
  { day: 2, hours: 48, label: 'Day 2 (+48h)' },
  { day: 3, hours: 72, label: 'Day 3 (+72h)' },
  { day: 4, hours: 96, label: 'Day 4 (+96h)' },
  { day: 5, hours: 120, label: 'Day 5 (+120h)' },
  { day: 6, hours: 144, label: 'Day 6 (+144h)' },
  { day: 7, hours: 168, label: 'Day 7 (+168h)' },
  { day: 8, hours: 192, label: 'Day 8 (+192h)' },
  { day: 9, hours: 216, label: 'Day 9 (+216h)' },
  { day: 10, hours: 240, label: 'Day 10 (+240h)' },
];

export const REGIONS = [
  {
    id: 'Western Himalaya',
    name: 'Western Himalaya (J&K/HP/Uttarakhand)',
    shortName: 'Western Himalaya',
    lat: [28.0, 36.0],
    lon: [73.0, 81.0],
  },
  {
    id: 'Northwest India',
    name: 'Northwest India (Punjab/Haryana/Rajasthan)',
    shortName: 'Northwest India',
    lat: [24.0, 32.0],
    lon: [69.0, 79.0],
  },
  {
    id: 'Indo-Gangetic Plain',
    name: 'Indo-Gangetic Plain (UP/Bihar)',
    shortName: 'Indo-Gangetic Plain',
    lat: [24.0, 30.0],
    lon: [79.0, 88.0],
  },
  {
    id: 'Northeast India',
    name: 'Northeast India',
    shortName: 'Northeast India',
    lat: [22.0, 29.5],
    lon: [88.0, 97.5],
  },
  {
    id: 'Central India',
    name: 'Central India (MP/Chhattisgarh/Vidarbha)',
    shortName: 'Central India',
    lat: [18.0, 26.0],
    lon: [74.0, 84.0],
  },
  {
    id: 'West Coast',
    name: 'West Coast (Konkan/Goa/Kerala)',
    shortName: 'West Coast',
    lat: [8.0, 20.0],
    lon: [72.0, 77.0],
  },
  {
    id: 'East Coast',
    name: 'East Coast (Andhra/Odisha/TN coast)',
    shortName: 'East Coast',
    lat: [8.0, 20.0],
    lon: [78.0, 87.0],
  },
  {
    id: 'South Peninsula',
    name: 'South Peninsula (Interior Karnataka/TN)',
    shortName: 'South Peninsula',
    lat: [8.0, 16.0],
    lon: [74.5, 80.0],
  },
];

export const SEASONS = [
  { id: 'monsoon_JJAS', label: 'Monsoon (Jun–Sep / JJAS)' },
  { id: 'post_monsoon_ON', label: 'Post-Monsoon (Oct–Nov / ON)' },
  { id: 'winter_DJF', label: 'Winter (Dec–Feb / DJF)' },
  { id: 'pre_monsoon_MAM', label: 'Pre-Monsoon (Mar–May / MAM)' },
];

export const IMD_RAINFALL_CATEGORIES = [
  { id: 'no_rain', label: 'No Rain', range: '< 2.5 mm', min: 0, max: 2.5, color: '#475569' },
  { id: 'light', label: 'Light Rain', range: '2.5 – 15.5 mm', min: 2.5, max: 15.6, color: '#38BDF8' },
  { id: 'moderate', label: 'Moderate Rain', range: '15.6 – 64.4 mm', min: 15.6, max: 64.5, color: '#0284C7' },
  { id: 'heavy', label: 'Heavy Rain', range: '64.5 – 115.5 mm', min: 64.5, max: 115.6, color: '#F59E0B' },
  { id: 'very_heavy', label: 'Very Heavy', range: '115.6 – 204.4 mm', min: 115.6, max: 204.5, color: '#EA580C' },
  { id: 'extremely_heavy', label: 'Extremely Heavy', range: '≥ 204.5 mm', min: 204.5, max: Infinity, color: '#DC2626' },
];

export const BUST_RULES = {
  percentile: 0.90, // 90th percentile historical error
  tempHardThresholdK: 3.0, // >3.0 deg C absolute error is hard bust
  heavyRainMinIndex: 3, // index of 'heavy' in IMD categories
};
