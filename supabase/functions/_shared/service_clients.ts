// Service clients for edge functions. URLs reuse Railway env vars.
const QUANT_URL =
  Deno.env.get("QUANT_URL") ?? "http://localhost:8001";
const ORCHESTRATOR_URL =
  Deno.env.get("ORCHESTRATOR_URL") ?? "http://localhost:8002";
const GRAPH_URL =
  Deno.env.get("GRAPH_URL") ?? "http://localhost:8003";

async function serviceGet<T>(
  url: string,
  token?: string,
  retries = 2,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      return res.json() as Promise<T>;
    } catch (err) {
      if (attempt === retries) throw err;
      await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
    }
  }
  throw new Error("Unreachable");
}

async function servicePost<T>(
  url: string,
  body: unknown,
  token?: string,
  retries = 2,
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      return res.json() as Promise<T>;
    } catch (err) {
      if (attempt === retries) throw err;
      await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
    }
  }
  throw new Error("Unreachable");
}

export const quantClient = {
  metrics: (ticker: string, period?: string, token?: string) =>
    serviceGet(`${QUANT_URL}/metrics/${ticker}${period ? `?period=${period}` : ""}`, token),
  portfolioRisk: (tickers: string[], weights: number[], token?: string) =>
    servicePost(`${QUANT_URL}/portfolio/risk`, { tickers, weights }, token),
  valuation: (ticker: string, body: Record<string, unknown>, token?: string) =>
    servicePost(`${QUANT_URL}/valuation/${ticker}`, body, token),
  computeSnapshot: (portfolioId: string, token?: string) =>
    servicePost(`${QUANT_URL}/snapshot/${portfolioId}`, {}, token),
};

export const orchestratorClient = {
  analyzeTicker: (ticker: string, portfolioId?: string, token?: string) =>
    servicePost(`${ORCHESTRATOR_URL}/analyze`, { ticker, portfolio_id: portfolioId }, token, 2),
  dailyBrief: (portfolioId: string, date?: string, token?: string) =>
    serviceGet(
      `${ORCHESTRATOR_URL}/brief/${portfolioId}${date ? `?date=${date}` : ""}`,
      token,
      2,
    ),
};

export const graphClient = {
  hiddenConcentration: (tickers: string[], token?: string) =>
    servicePost(`${GRAPH_URL}/hidden-concentration`, { tickers }, token),
  themeExposure: (tickers: string[], token?: string) =>
    servicePost(`${GRAPH_URL}/theme-exposure`, { tickers }, token),
};
