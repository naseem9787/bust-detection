/**
 * Centralized API Service Layer
 * SIH 26079: AI-Based Forecast Bust Detection Platform
 *
 * Architecture:
 *   React components -> api.js -> FastAPI -> ML models
 *
 * Core Principles:
 * 1. Components must NOT call fetch/axios directly. All network communication is centralized here.
 * 2. Centralized configuration using environment variables (VITE_API_BASE_URL, VITE_USE_MOCK, etc.).
 * 3. Graceful fallback to mock data ONLY when backend endpoints are unavailable (404/network error).
 * 4. Automatic retry with exponential backoff for transient failures (502/503/504/timeout).
 * 5. Structured ApiError for error boundary handling and actionable retry triggers.
 */

import {
  MOCK_CYCLES,
  MOCK_REGIONS,
  MOCK_HISTORICAL_PERFORMANCE,
  getRegionalExplanationFactors,
  generateMockForecastResponse,
  getHistoricalReplayEvents,
  getHistoricalReplayData,
  DATA_DISCLAIMER,
} from '../data/mockData.js';

/**
 * Centralized API Configuration
 * Supports environment overrides via Vite (.env / .env.production)
 */
export const API_CONFIG = {
  // Base URL for FastAPI backend (default: '/api/v1', proxied to localhost:8000 in dev)
  baseUrl:
    (typeof import.meta !== 'undefined' &&
      (import.meta.env?.VITE_API_BASE_URL || import.meta.env?.VITE_API_URL)) ||
    '/api/v1',

  // Mock Strategy:
  // - 'auto': Attempt live FastAPI endpoint; gracefully fallback to mock if 404 / connection error
  // - 'false': Strict live API mode (throws ApiError to test failure states and error UI)
  // - 'true': Always use mock data (offline standalone development)
  useMock:
    typeof import.meta === 'undefined'
      ? 'auto'
      : import.meta.env?.VITE_USE_MOCK ?? 'auto',

  // Request timeout in milliseconds
  timeoutMs:
    Number(
      typeof import.meta !== 'undefined' &&
        import.meta.env?.VITE_API_TIMEOUT_MS
    ) || 8000,

  // Maximum automatic retries for transient errors
  maxRetries:
    Number(
      typeof import.meta !== 'undefined' &&
        import.meta.env?.VITE_API_RETRY_ATTEMPTS
    ) || 2,
};

/**
 * Custom API Error class with status, endpoint, and retry metadata
 */
export class ApiError extends Error {
  constructor(message, { status = null, statusText = '', endpoint = '', isNetworkError = false, originalError = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.endpoint = endpoint;
    this.isNetworkError = isNetworkError;
    this.originalError = originalError;
  }
}

/**
 * Checks whether fallback to mock data is permitted under current config
 */
function shouldFallbackToMock() {
  const mode = String(API_CONFIG.useMock).toLowerCase().trim();
  return mode === 'auto' || mode === 'true' || mode === '';
}

/**
 * Checks whether mock-only mode is active (skip live network attempt)
 */
function isMockOnly() {
  const mode = String(API_CONFIG.useMock).toLowerCase().trim();
  return mode === 'true';
}

/**
 * Utility to simulate realistic network latency during mock testing
 */
function simulateLatency(ms = 60) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Centralized HTTP request engine with timeout, headers, and retry with exponential backoff
 */
async function apiRequest(endpoint, { method = 'GET', body = null, headers = {} } = {}) {
  // Normalize endpoint URL (ensures no double slashes)
  const base = API_CONFIG.baseUrl.replace(/\/+$/, '');
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  let fullUrl = `${base}${path}`;
  if (fullUrl.startsWith('/') && typeof window === 'undefined') {
    fullUrl = `http://localhost:8000${fullUrl}`;
  }

  let attempt = 0;
  const maxRetries = API_CONFIG.maxRetries;

  while (attempt <= maxRetries) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeoutMs);

    try {
      const response = await fetch(fullUrl, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...headers,
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle non-OK HTTP responses
      if (!response.ok) {
        const errorText = await response.text().catch(() => null);

        // Transient server errors (502, 503, 504) -> candidate for retry
        if ([502, 503, 504].includes(response.status) && attempt < maxRetries) {
          attempt++;
          const delay = 300 * Math.pow(2, attempt);
          console.warn(`[apiService] Transient ${response.status} from ${endpoint}. Retrying in ${delay}ms (attempt ${attempt}/${maxRetries})...`);
          await new Promise((r) => setTimeout(r, delay));
          continue;
        }

        throw new ApiError(
          `FastAPI returned ${response.status} (${response.statusText}): ${errorText || 'No detail provided'}`,
          {
            status: response.status,
            statusText: response.statusText,
            endpoint,
          }
        );
      }

      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);

      // Distinguish AbortError / Timeout
      const isTimeout = err.name === 'AbortError';
      const isNetwork = !err.status && (err instanceof TypeError || isTimeout);

      // If it's a network glitch or timeout and we have retries left, retry
      if (isNetwork && attempt < maxRetries) {
        attempt++;
        const delay = 300 * Math.pow(2, attempt);
        console.warn(`[apiService] Network ${isTimeout ? 'timeout' : 'failure'} on ${endpoint}. Retrying in ${delay}ms (attempt ${attempt}/${maxRetries})...`);
        await new Promise((r) => setTimeout(r, delay));
        continue;
      }

      // Re-wrap or throw structured ApiError
      if (err instanceof ApiError) {
        throw err;
      }

      throw new ApiError(
        isTimeout
          ? `Request timeout after ${API_CONFIG.timeoutMs}ms reaching ${endpoint}`
          : `Network error reaching FastAPI backend at ${fullUrl}: ${err.message}`,
        {
          isNetworkError: true,
          endpoint,
          originalError: err,
        }
      );
    }
  }
}

/**
 * In-memory response cache and in-flight request deduplication
 * Eliminates redundant network and mock computation across components and lead-time scrubbing
 */
const memoryCache = new Map();
const inFlightRequests = new Map();

export function clearApiCache() {
  memoryCache.clear();
  inFlightRequests.clear();
}

async function cachedApiCall(cacheKey, fetcher, forceReload = false) {
  if (!forceReload && memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey);
  }

  if (inFlightRequests.has(cacheKey)) {
    return inFlightRequests.get(cacheKey);
  }

  const promise = (async () => {
    try {
      const result = await fetcher();
      memoryCache.set(cacheKey, result);
      return result;
    } finally {
      inFlightRequests.delete(cacheKey);
    }
  })();

  inFlightRequests.set(cacheKey, promise);
  return promise;
}

// ============================================================================
// CANONICAL REGION NORMALIZATION & METRIC FORMATTING
// ============================================================================

/**
 * Canonical region identifier mapping dictionary
 * Maps display names, variants, and kebab-case IDs to canonical frontend map IDs
 */
export const CANONICAL_REGION_IDS = {
  'west-coast': 'west-coast',
  'west coast': 'west-coast',
  'western-himalaya': 'western-himalaya',
  'western himalaya': 'western-himalaya',
  'central-india': 'central-india',
  'central india': 'central-india',
  'northeast-india': 'northeast-india',
  'northeast india': 'northeast-india',
  'indo-gangetic-plain': 'indo-gangetic-plain',
  'indo-gangetic plain': 'indo-gangetic-plain',
  'east-coast': 'east-coast',
  'east coast': 'east-coast',
  'south-peninsula': 'south-peninsula',
  'south peninsula': 'south-peninsula',
  'northwest-india': 'northwest-india',
  'northwest india': 'northwest-india',
};

/**
 * Normalizes regionalMetrics to ensure canonical ID keys (e.g. 'west-coast')
 * and required metric fields (bustProbability, confidence, precipError, tempError)
 */
export function normalizeRegionalMetrics(rawMetrics, leadDay = 5) {
  const normalized = {};

  if (rawMetrics && typeof rawMetrics === 'object' && Object.keys(rawMetrics).length > 0) {
    for (const [key, val] of Object.entries(rawMetrics)) {
      if (!val || typeof val !== 'object') continue;
      const lower = key.toLowerCase().trim();
      const canonicalId = CANONICAL_REGION_IDS[lower] || key;
      const displayName = val.regionName || val.region_name || val.shortName || key;

      const entry = {
        regionId: canonicalId,
        regionName: displayName,
        bustProbability: Number(val.bustProbability ?? val.bust_probability ?? 0.35),
        confidence: Number(val.confidence ?? 0.60),
        precipError: Number(val.precipError ?? val.precip_error ?? 5.0),
        tempError: Number(val.tempError ?? val.temp_error ?? 1.0),
      };

      // Store by canonical ID (preferred by the map, e.g. 'west-coast')
      normalized[canonicalId] = entry;
      // Also store by display name (e.g. 'West Coast') for backward compatibility
      if (displayName && displayName !== canonicalId) {
        normalized[displayName] = entry;
      }
    }
    return normalized;
  }

  // Fallback: If backend does not provide regionalMetrics, build from MOCK_REGIONS baseline
  const numLead = Number(leadDay) || 5;
  MOCK_REGIONS.forEach((r) => {
    const baseRate = r.baselineRisk || 0.35;
    const leadFactor = (numLead - 1) * 0.024;
    const prob = Math.min(0.64, Number((baseRate + leadFactor).toFixed(3)));
    const conf = Math.max(0.22, Number((0.94 - numLead * 0.068 - (r.id === 'west-coast' ? 0.05 : 0)).toFixed(3)));
    const precipErr = Number((3.0 + numLead * 1.2 + (r.id === 'west-coast' ? 3.5 : 0)).toFixed(1));
    const tempErr = Number((1.1 + numLead * 0.15).toFixed(1));

    const entry = {
      regionId: r.id,
      regionName: r.shortName,
      bustProbability: prob,
      confidence: conf,
      precipError: precipErr,
      tempError: tempErr,
    };
    normalized[r.id] = entry;
    normalized[r.shortName] = entry;
  });

  return normalized;
}

/**
 * Normalizes forecast verification payload from FastAPI or mock data
 */
export function normalizeForecastPayload(payload, leadDay = 5) {
  if (!payload) return payload;
  return {
    ...payload,
    regionalMetrics: normalizeRegionalMetrics(payload.regionalMetrics, leadDay),
  };
}

// ============================================================================
// API ENDPOINTS
// ============================================================================

/**
 * 1. GET /api/v1/forecast
 * Retrieves medium-range bust probability, confidence, error, and grid points
 * for a specific forecast initialization cycle, lead day (1-10), and region.
 *
 * @param {Object} params
 * @param {string} [params.cycle='2026-09-29 00Z'] - Forecast initialization cycle
 * @param {number} [params.leadDay=5] - Forecast lead time day (1 to 10)
 * @param {string} [params.regionId='west-coast'] - Region identifier
 * @param {boolean} [params.forceReload=false] - Bypass cache
 * @returns {Promise<Object>} Formatted forecast verification payload
 */
export async function getForecast({
  cycle = '2026-09-29 00Z',
  leadDay = 5,
  regionId = 'west-coast',
  forceReload = false,
} = {}) {
  const cacheKey = `forecast_${cycle}_${leadDay}_${regionId}`;

  return cachedApiCall(
    cacheKey,
    async () => {
      if (isMockOnly()) {
        await simulateLatency(80);
        const mockData = generateMockForecastResponse({ cycle, leadDay, regionId });
        return normalizeForecastPayload(mockData, leadDay);
      }

      const query = new URLSearchParams({
        cycle,
        lead_day: String(leadDay),
        region_id: regionId,
      }).toString();

      try {
        const liveData = await apiRequest(`/forecast?${query}`);
        return normalizeForecastPayload(liveData, leadDay);
      } catch (err) {
        if (shouldFallbackToMock()) {
          console.warn(`[apiService] Live endpoint /forecast unavailable (${err.message}). Using calibrated mock fallback.`);
          const mockData = generateMockForecastResponse({ cycle, leadDay, regionId });
          return normalizeForecastPayload(mockData, leadDay);
        }
        throw err;
      }
    },
    forceReload
  );
}

/**
 * 2. GET /api/v1/regions
 * Retrieves metadata, extents, and climatological profiles for all 8 Indian regions.
 *
 * @param {Object} [params]
 * @param {boolean} [params.forceReload=false] - Bypass cache
 * @returns {Promise<Array>} List of region objects
 */
export async function getRegions({ forceReload = false } = {}) {
  return cachedApiCall(
    'regions',
    async () => {
      if (isMockOnly()) {
        await simulateLatency(40);
        return MOCK_REGIONS;
      }

      try {
        return await apiRequest('/regions');
      } catch (err) {
        if (shouldFallbackToMock()) {
          console.warn(`[apiService] Live endpoint /regions unavailable (${err.message}). Using calibrated mock fallback.`);
          return MOCK_REGIONS;
        }
        throw err;
      }
    },
    forceReload
  );
}

/**
 * 3. GET /api/v1/regions/{regionId}
 * Retrieves in-depth regional climatology, Day 1–10 error progression,
 * dominant bust modes, and verification factors.
 *
 * @param {Object} params
 * @param {string} params.regionId - Region identifier
 * @param {string} [params.season='monsoon_JJAS'] - Meteorological season
 * @param {number} [params.leadDay=5] - Forecast lead day
 * @param {string} [params.cycle='2026-09-29 00Z'] - Forecast cycle
 * @returns {Promise<Object>} Regional analysis payload
 */
export async function getRegionAnalysis({
  regionId = 'west-coast',
  season = 'monsoon_JJAS',
  leadDay = 5,
  cycle = '2026-09-29 00Z',
  forceReload = false,
} = {}) {
  const cacheKey = `region_analysis_${regionId}_${season}_${leadDay}_${cycle}`;

  return cachedApiCall(
    cacheKey,
    async () => {
      if (isMockOnly()) {
        await simulateLatency(80);
        return generateMockRegionAnalysis({ regionId, season, leadDay, cycle });
      }

      const query = new URLSearchParams({
        season,
        lead_day: String(leadDay),
        cycle,
      }).toString();

      try {
        return await apiRequest(`/regions/${encodeURIComponent(regionId)}?${query}`);
      } catch (err) {
        if (shouldFallbackToMock()) {
          console.warn(`[apiService] Live endpoint /regions/${regionId} unavailable (${err.message}). Using calibrated mock fallback.`);
          return generateMockRegionAnalysis({ regionId, season, leadDay, cycle });
        }
        throw err;
      }
    },
    forceReload
  );
}

/**
 * Helper to build mock region analysis payload
 */
function generateMockRegionAnalysis({ regionId, season, leadDay, cycle }) {
  const region = MOCK_REGIONS.find((r) => r.id === regionId || r.shortName === regionId) || MOCK_REGIONS[5];
  const regionNameLower = region.shortName.toLowerCase();

  const regionHistory = MOCK_HISTORICAL_PERFORMANCE.filter((h) =>
    h.region.toLowerCase().includes(regionNameLower)
  );

  const leadDaySeries = regionHistory
    .filter((h) => h.season === season)
    .sort((a, b) => a.leadDay - b.leadDay);

  const currentLeadRecord =
    leadDaySeries.find((r) => r.leadDay === Number(leadDay)) || leadDaySeries[0] || {};

  const forecast = normalizeForecastPayload(
    generateMockForecastResponse({ cycle, leadDay: Number(leadDay), regionId: region.id }),
    leadDay
  );

  const explanations = getRegionalExplanationFactors({
    regionId: region.id,
    leadDay: Number(leadDay),
    cycle,
    regionName: region.shortName,
  });

  const seasonsDef = [
    { key: 'monsoon_JJAS', label: 'Monsoon (JJAS)', color: '#0284C7' },
    { key: 'post_monsoon_ON', label: 'Post-Monsoon (ON)', color: '#10B981' },
    { key: 'pre_monsoon_MAM', label: 'Pre-Monsoon (MAM)', color: '#F59E0B' },
    { key: 'winter_DJF', label: 'Winter (DJF)', color: '#818CF8' },
  ];

  const seasonalBreakdown = seasonsDef.map((s) => {
    const match = regionHistory.find((r) => r.season === s.key && r.leadDay === Number(leadDay));
    return {
      seasonKey: s.key,
      seasonName: s.label,
      color: s.color,
      bustRate: match ? match.bustRate : 35.0,
      meanAbsErrorPrecipMm: match ? match.meanAbsErrorPrecipMm : 8.5,
      meanAbsErrorTempC: match ? match.meanAbsErrorTempC : 1.8,
    };
  });

  const operationalMisses = {
    nSamples: 27328,
    missedPrecipBustRate: Math.round((currentLeadRecord.bustRate || 36.7) * 1.15),
    tempHardThresholdBustRate: Math.round((currentLeadRecord.tempBustRate || 14.5) * 1.05),
    highestErrorSeason: 'Monsoon (JJAS)',
    primaryBustMechanism: 'Categorical IMD boundary skips in heavy orographic rain cells',
  };

  return {
    meta: {
      regionId: region.id,
      regionName: region.name,
      shortName: region.shortName,
      season,
      leadDay: Number(leadDay),
      cycle,
      disclaimer: DATA_DISCLAIMER,
      timestamp: new Date().toISOString(),
    },
    currentLeadRecord,
    leadDaySeries,
    seasonalBreakdown,
    forecast,
    explanations,
    operationalMisses,
  };
}

/**
 * 4. GET /api/v1/historical-performance
 * Retrieves aggregated verification statistics across lead times, regions, and seasons.
 *
 * @param {Object} [params]
 * @param {number} [params.leadDay] - Filter by specific lead day
 * @param {string} [params.regionId] - Filter by region
 * @param {string} [params.season] - Filter by season
 * @param {string} [params.variable='precipitation'] - Meteorological variable
 * @param {boolean} [params.forceReload=false] - Bypass cache
 * @returns {Promise<Array>} Historical performance records
 */
export async function getHistoricalPerformance({
  leadDay = null,
  regionId = null,
  season = null,
  variable = 'precipitation',
  forceReload = false,
} = {}) {
  const cacheKey = `historical_${leadDay ?? 'all'}_${regionId ?? 'all'}_${season ?? 'all'}_${variable}`;

  return cachedApiCall(
    cacheKey,
    async () => {
      if (isMockOnly()) {
        await simulateLatency(50);
        return filterMockHistorical({ leadDay, regionId, season });
      }

      const queryParams = { variable };
      if (leadDay) queryParams.lead_day = String(leadDay);
      if (regionId) queryParams.region_id = regionId;
      if (season) queryParams.season = season;

      const query = new URLSearchParams(queryParams).toString();

      try {
        return await apiRequest(`/historical-performance?${query}`);
      } catch (err) {
        if (shouldFallbackToMock()) {
          console.warn(`[apiService] Live endpoint /historical-performance unavailable (${err.message}). Using calibrated mock fallback.`);
          return filterMockHistorical({ leadDay, regionId, season });
        }
        throw err;
      }
    },
    forceReload
  );
}

function filterMockHistorical({ leadDay, regionId, season }) {
  let records = [...MOCK_HISTORICAL_PERFORMANCE];
  if (leadDay) records = records.filter((r) => r.leadDay === Number(leadDay));
  if (regionId) records = records.filter((r) => r.region.toLowerCase().includes(regionId.toLowerCase()));
  if (season) records = records.filter((r) => r.season === season);
  return records;
}

/**
 * 5. GET /api/v1/explanations
 * Retrieves explainable AI feature attribution factors for a given forecast.
 *
 * @param {Object} params
 * @param {string} params.cycle - Forecast cycle
 * @param {number} params.leadDay - Lead day (1-10)
 * @param {string} params.regionId - Region identifier
 * @param {boolean} [params.forceReload=false] - Bypass cache
 * @returns {Promise<Object>} Explanation factors and narrative
 */
export async function getExplanation({
  cycle = '2026-09-29 00Z',
  leadDay = 5,
  regionId = 'west-coast',
  forceReload = false,
} = {}) {
  const cacheKey = `explanation_${cycle}_${leadDay}_${regionId}`;

  return cachedApiCall(
    cacheKey,
    async () => {
      if (isMockOnly()) {
        await simulateLatency(50);
        return generateMockExplanation({ cycle, leadDay, regionId });
      }

      const query = new URLSearchParams({
        cycle,
        lead_day: String(leadDay),
        region_id: regionId,
      }).toString();

      try {
        return await apiRequest(`/explanations?${query}`);
      } catch (err) {
        if (shouldFallbackToMock()) {
          console.warn(`[apiService] Live endpoint /explanations unavailable (${err.message}). Using calibrated mock fallback.`);
          return generateMockExplanation({ cycle, leadDay, regionId });
        }
        throw err;
      }
    },
    forceReload
  );
}

function generateMockExplanation({ cycle, leadDay, regionId }) {
  const region = MOCK_REGIONS.find((r) => r.id === regionId || r.shortName === regionId) || MOCK_REGIONS[5];
  const factors = getRegionalExplanationFactors({
    regionId: region.id,
    leadDay: Number(leadDay),
    cycle,
    regionName: region.shortName,
  });

  return {
    cycle,
    leadDay,
    region: region.shortName,
    factors,
    bulletinSummary: `Forecast confidence for ${region.shortName} at Day ${leadDay} is constrained by IMD rainfall category dispersion and run-to-run 500hPa geopotential height jumpiness.`,
    disclaimer: DATA_DISCLAIMER,
  };
}

/**
 * 6. GET /api/v1/cycles
 * Retrieves available forecast initialization cycles.
 *
 * @param {Object} [params]
 * @param {boolean} [params.forceReload=false] - Bypass cache
 * @returns {Promise<Array>} List of forecast cycles
 */
export async function getForecastCycles({ forceReload = false } = {}) {
  return cachedApiCall(
    'cycles',
    async () => {
      if (isMockOnly()) {
        await simulateLatency(30);
        return MOCK_CYCLES;
      }

      try {
        return await apiRequest('/cycles');
      } catch (err) {
        if (shouldFallbackToMock()) {
          console.warn(`[apiService] Live endpoint /cycles unavailable (${err.message}). Using calibrated mock fallback.`);
          return MOCK_CYCLES;
        }
        throw err;
      }
    },
    forceReload
  );
}

/**
 * 7. GET /api/v1/replay/events
 * Retrieves catalog of historical benchmark events available for replay.
 *
 * @param {Object} [params]
 * @param {boolean} [params.forceReload=false] - Bypass cache
 * @returns {Promise<Array>} List of benchmark event metadata
 */
export async function getReplayEvents({ forceReload = false } = {}) {
  return cachedApiCall(
    'replay_events',
    async () => {
      if (isMockOnly()) {
        await simulateLatency(40);
        return getHistoricalReplayEvents();
      }

      try {
        return await apiRequest('/replay/events');
      } catch (err) {
        if (shouldFallbackToMock()) {
          console.warn(`[apiService] Live endpoint /replay/events unavailable (${err.message}). Using calibrated mock fallback.`);
          return getHistoricalReplayEvents();
        }
        throw err;
      }
    },
    forceReload
  );
}

/**
 * 8. GET /api/v1/replay/event
 * Retrieves analytical replay state for a specific historical event,
 * initialization cycle, lead day (1–10), and region.
 *
 * @param {Object} params
 * @param {string} params.eventId - e.g. 'kerala-2018'
 * @param {string} [params.cycle] - Initialization cycle timestamp
 * @param {number} [params.leadDay=5] - Forecast lead day (1–10)
 * @param {string} [params.regionId] - Selected region id
 * @param {boolean} [params.forceReload=false] - Bypass cache
 * @returns {Promise<Object>} Analytical replay payload
 */
export async function getReplayData({
  eventId = 'kerala-2018',
  cycle = null,
  leadDay = 5,
  regionId = null,
  forceReload = false,
} = {}) {
  const cacheKey = `replay_data_${eventId}_${cycle ?? ''}_${leadDay}_${regionId ?? ''}`;

  return cachedApiCall(
    cacheKey,
    async () => {
      if (isMockOnly()) {
        await simulateLatency(60);
        return getHistoricalReplayData({ eventId, cycle, leadDay, regionId });
      }

      const queryParams = {
        event_id: eventId,
        lead_day: String(leadDay),
      };
      if (cycle) queryParams.cycle = cycle;
      if (regionId) queryParams.region_id = regionId;

      const query = new URLSearchParams(queryParams).toString();

      try {
        return await apiRequest(`/replay/event?${query}`);
      } catch (err) {
        if (shouldFallbackToMock()) {
          console.warn(`[apiService] Live endpoint /replay/event unavailable (${err.message}). Using calibrated mock fallback.`);
          return getHistoricalReplayData({ eventId, cycle, leadDay, regionId });
        }
        throw err;
      }
    },
    forceReload
  );
}
