import { AuthError, corsHeaders, errorResponse, getSupabaseAdmin, jsonResponse, requireAuth } from "../_shared/auth.ts";

const ORCHESTRATOR_URL = Deno.env.get("ORCHESTRATOR_URL") ?? "http://localhost:8002";

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders() });
  }

  try {
    await requireAuth(req);
    const { tickers } = await req.json();

    if (!Array.isArray(tickers) || tickers.length < 2 || tickers.length > 4) {
      return errorResponse("Provide 2–4 tickers");
    }
    const syms: string[] = tickers.map((t: string) => t.toUpperCase().trim());
    for (const sym of syms) {
      if (!/^[A-Z0-9.^=-]{1,7}$/.test(sym)) {
        return errorResponse(`Invalid ticker: ${sym}`);
      }
    }

    const token = req.headers.get("Authorization")?.slice(7);
    const res = await fetch(`${ORCHESTRATOR_URL}/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ tickers: syms }),
    });

    if (!res.ok) {
      return errorResponse(`Orchestrator error: ${res.status}`, 502);
    }
    return jsonResponse(await res.json());
  } catch (err) {
    if (err instanceof AuthError) return errorResponse(err.message, 401);
    return errorResponse(err instanceof Error ? err.message : "Internal error", 500);
  }
});
