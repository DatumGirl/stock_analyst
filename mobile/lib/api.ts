import { supabase } from './supabase';
import type { ApiOk, ApiError } from './types';

const QUANT_URL = process.env.EXPO_PUBLIC_QUANT_API_URL ?? 'http://localhost:8001';
const GRAPH_URL = process.env.EXPO_PUBLIC_GRAPH_API_URL ?? 'http://localhost:8003';
const ORCHESTRATOR_URL = process.env.EXPO_PUBLIC_ORCHESTRATOR_API_URL ?? 'http://localhost:8002';

// ─── Direct service helpers (quant + graph, read-only) ───────────────────────

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

async function get<T>(base: string, path: string, params?: Record<string, string>, retries = 0): Promise<ApiOk<T>> {
  const headers = await authHeaders();
  const url = new URL(`${base}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }

  let res: Response;
  try {
    res = await fetch(url.toString(), { headers });
  } catch {
    if (retries > 0) {
      await new Promise(r => setTimeout(r, 5000));
      return get(base, path, params, retries - 1);
    }
    throw new Error('Network request failed — check your connection');
  }

  if (!res.ok) {
    const raw = await res.text().catch(() => '');
    let errMsg: string;
    try {
      const err: ApiError = JSON.parse(raw);
      errMsg = err.detail ?? err.error;
    } catch {
      const preview = raw.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 200);
      if (retries > 0) {
        await new Promise(r => setTimeout(r, 5000));
        return get(base, path, params, retries - 1);
      }
      throw new Error(`HTTP ${res.status}: ${preview || 'empty response'}`);
    }
    throw new Error(errMsg);
  }
  return res.json();
}

async function post<T>(base: string, path: string, body: unknown, retries = 0): Promise<ApiOk<T>> {
  const headers = await authHeaders();

  let res: Response;
  try {
    res = await fetch(`${base}${path}`, { method: 'POST', headers, body: JSON.stringify(body) });
  } catch {
    if (retries > 0) {
      await new Promise(r => setTimeout(r, 5000));
      return post(base, path, body, retries - 1);
    }
    throw new Error('Network request failed — check your connection');
  }

  if (!res.ok) {
    const raw = await res.text().catch(() => '');
    let errMsg: string;
    try {
      const err: ApiError = JSON.parse(raw);
      errMsg = err.detail ?? err.error;
    } catch {
      const preview = raw.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 200);
      if (retries > 0) {
        await new Promise(r => setTimeout(r, 5000));
        return post(base, path, body, retries - 1);
      }
      throw new Error(`HTTP ${res.status}: ${preview || 'empty response'}`);
    }
    throw new Error(errMsg);
  }
  return res.json();
}

// ─── Edge Function helper (orchestrator — JWT-gated) ─────────────────────────

async function invokeFunction<T>(name: string, body?: unknown): Promise<ApiOk<T>> {
  const { data, error } = await supabase.functions.invoke(name, { body });
  if (error) throw new Error(error.message);
  return data as ApiOk<T>;
}

// ─── Quant service ───────────────────────────────────────────────────────────

export const quantApi = {
  metrics: (ticker: string, period?: string) =>
    get(QUANT_URL, `/metrics/${ticker}`, period ? { period } : undefined),

  portfolioRisk: (tickers: string[], weights: number[]) =>
    post(QUANT_URL, '/portfolio/risk', { tickers, weights }),

  valuation: (ticker: string, currentPrice: number, fundamentals?: Record<string, number>) =>
    post(QUANT_URL, `/valuation/${ticker}`, { ticker, current_price: currentPrice, ...fundamentals }),

  computeSnapshot: (portfolioId: string) =>
    post(QUANT_URL, `/snapshot/${portfolioId}`, {}),

  ingestTicker: (ticker: string) =>
    post(QUANT_URL, `/ingest/${ticker}`, {}),
};

// ─── Orchestrator (direct Railway call — same pattern as quant/graph) ────────

export const orchestratorApi = {
  analyzeTicker: (ticker: string, portfolio_id?: string) =>
    post(ORCHESTRATOR_URL, '/analyze', { ticker, portfolio_id }, 2),

  compareTickers: (tickers: string[]) =>
    post(ORCHESTRATOR_URL, '/compare', { tickers }, 2),

  dailyBrief: (portfolio_id: string, date?: string) =>
    get(ORCHESTRATOR_URL, `/brief/${portfolio_id}`, date ? { date } : undefined, 2),
};

// ─── Graph service ────────────────────────────────────────────────────────────

export const graphApi = {
  relationships: (ticker: string) =>
    get(GRAPH_URL, `/relationships/${ticker}`),

  supplyChain: (ticker: string) =>
    get(GRAPH_URL, `/supply-chain/${ticker}`),

  hiddenConcentration: (tickers: string[]) =>
    post(GRAPH_URL, '/hidden-concentration', { tickers }),

  etfOverlap: (tickers: string[]) =>
    post(GRAPH_URL, '/etf-overlap', { tickers }),

  themeExposure: (tickers: string[]) =>
    post(GRAPH_URL, '/theme-exposure', { tickers }),
};
