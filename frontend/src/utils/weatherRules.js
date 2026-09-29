/**
 * Meteorological Rules & Bust Classification Utilities
 * Directly mirroring Python src/label_busts.py logic
 */

import { IMD_RAINFALL_CATEGORIES } from '../design-system/weather-tokens.js';

/**
 * Returns IMD rainfall category descriptor given 24h accumulated rainfall in mm
 */
export function getRainfallCategory(mm) {
  if (mm === null || mm === undefined || isNaN(mm) || mm < 0) {
    return IMD_RAINFALL_CATEGORIES[0];
  }
  for (const cat of IMD_RAINFALL_CATEGORIES) {
    if (mm <= cat.max) {
      return cat;
    }
  }
  return IMD_RAINFALL_CATEGORIES[IMD_RAINFALL_CATEGORIES.length - 1];
}

/**
 * Evaluates Bust Risk Level from calculated bust probability (0.0 to 1.0 or 0 to 100%)
 */
export function getBustRiskLevel(probability) {
  const p = probability > 1 ? probability / 100 : probability;
  if (p >= 0.45) return 'extreme';
  if (p >= 0.35) return 'high';
  if (p >= 0.25) return 'elevated';
  if (p >= 0.15) return 'moderate';
  return 'low';
}

/**
 * Evaluates Forecast Confidence Tier from calibrated confidence score (0.0 to 1.0)
 */
export function getConfidenceTier(confidence) {
  const c = confidence > 1 ? confidence / 100 : confidence;
  if (c >= 0.80) return 'high';
  if (c >= 0.50) return 'moderate';
  return 'low';
}

/**
 * Checks whether rainfall error constitutes an IMD categorical bust
 * Rule: >=2 categorical difference OR missed/false alarm heavy rain event
 */
export function isRainfallCategoricalBust(fcstMm, obsMm) {
  const fcstCat = getRainfallCategory(fcstMm);
  const obsCat = getRainfallCategory(obsMm);
  const fcstIndex = IMD_RAINFALL_CATEGORIES.findIndex((c) => c.id === fcstCat.id);
  const obsIndex = IMD_RAINFALL_CATEGORIES.findIndex((c) => c.id === obsCat.id);

  const gap = Math.abs(fcstIndex - obsIndex);
  const heavyIndex = 3; // IMD "heavy"
  const missedHeavy = obsIndex >= heavyIndex && fcstIndex < heavyIndex;
  const falseAlarmHeavy = fcstIndex >= heavyIndex && obsIndex < heavyIndex;

  return {
    isBust: gap >= 2 || missedHeavy || falseAlarmHeavy,
    gap,
    missedHeavy,
    falseAlarmHeavy,
    fcstCat,
    obsCat,
  };
}
