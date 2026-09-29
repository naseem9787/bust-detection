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
 * Evaluates forecast bust risk level from the real calibrated bust
 * probability (0.0 to 1.0 or 0 to 100%).
 *
 * These cutoffs are based on the REAL distribution of the production
 * model's calibrated output across all 29 states and all 10 lead days
 * (computed directly from the backend, not assumed): most states sit
 * under 0.5% chance of a major forecast error, with a long tail of rarer,
 * genuinely higher-risk cases up to ~15%. Round numbers close to the
 * 75th/90th/97th percentiles of that real distribution were chosen -
 * NOT arbitrary percentages, and NOT the old mock-data thresholds (45%
 * "extreme"), which never triggered on real, honest model output.
 */
export function getBustRiskLevel(probability) {
  const p = probability > 1 ? probability / 100 : probability;
  if (p >= 0.06) return 'high';
  if (p >= 0.03) return 'elevated';
  if (p >= 0.01) return 'moderate';
  return 'low';
}

/**
 * Evaluates forecast reliability tier from reliability = 1 - bust probability.
 * Matches getBustRiskLevel's real-data-based cutoffs exactly (inverted):
 * reliability >=97% <-> risk <3%, etc. - never a separately invented scale.
 */
export function getConfidenceTier(confidence) {
  const c = confidence > 1 ? confidence / 100 : confidence;
  if (c >= 0.97) return 'high';
  if (c >= 0.94) return 'moderate';
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
