/**
 * Scientific & Meteorological Formatters
 * Formats measurements with strict unit conventions and tabular alignment
 */

export function formatPrecip(mm, decimals = 1) {
  if (mm === null || mm === undefined || isNaN(mm)) return '—';
  return `${Number(mm).toFixed(decimals)} mm`;
}

export function formatTemp(degC, decimals = 1) {
  if (degC === null || degC === undefined || isNaN(degC)) return '—';
  const prefix = degC > 0 ? '+' : '';
  return `${prefix}${Number(degC).toFixed(decimals)} °C`;
}

export function formatPressure(hPa, decimals = 1) {
  if (hPa === null || hPa === undefined || isNaN(hPa)) return '—';
  return `${Number(hPa).toFixed(decimals)} hPa`;
}

export function formatPercent(rate, decimals = 1) {
  if (rate === null || rate === undefined || isNaN(rate)) return '—';
  return `${Number(rate).toFixed(decimals)}%`;
}

export function formatLeadTime(day) {
  const hours = Number(day) * 24;
  return `Day ${day} (+${hours}h)`;
}

export function formatCoordinates(lat, lon) {
  const latDir = lat >= 0 ? '°N' : '°S';
  const lonDir = lon >= 0 ? '°E' : '°W';
  return `${Math.abs(lat).toFixed(1)}${latDir}, ${Math.abs(lon).toFixed(1)}${lonDir}`;
}

export function formatCycleTimestamp(date = new Date(), cycle = '00Z') {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd} ${cycle}`;
}
