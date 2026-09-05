// Called by pg_cron at 16:15 ET daily and on-demand from mobile app.
import { corsHeaders, errorResponse, getSupabaseAdmin, jsonResponse } from "../_shared/auth.ts";
import { quantClient } from "../_shared/service_clients.ts";

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders() });
  }

  const admin = getSupabaseAdmin();
  const errors: string[] = [];
  let processed = 0;

  try {
    const body = req.headers.get("content-length") !== "0" ? await req.json().catch(() => ({})) : {};
    const specificPortfolioId: string | undefined = body.portfolio_id;

    // Get portfolios to process
    let portfoliosQuery = admin.from("portfolios").select("id, user_id");
    if (specificPortfolioId) {
      portfoliosQuery = portfoliosQuery.eq("id", specificPortfolioId);
    }
    const { data: portfolios, error: pErr } = await portfoliosQuery;
    if (pErr || !portfolios) {
      return errorResponse(`Failed to fetch portfolios: ${pErr?.message}`, 500);
    }

    const today = new Date().toISOString().split("T")[0];

    for (const portfolio of portfolios) {
      try {
        // Fetch positions
        const { data: positions } = await admin
          .from("positions")
          .select("ticker, quantity, cost_basis")
          .eq("portfolio_id", portfolio.id);

        if (!positions?.length) continue;

        const tickers = positions.map((p: any) => p.ticker);

        // Fetch latest prices
        const priceMap: Record<string, number> = {};
        for (const ticker of tickers) {
          const { data: prices } = await admin
            .from("prices_daily")
            .select("close")
            .eq("ticker", ticker)
            .order("date", { ascending: false })
            .limit(1);
          if (prices?.[0]) priceMap[ticker] = parseFloat(prices[0].close);
        }

        // Compute total value and weights
        let totalValue = 0;
        const weights: number[] = [];
        for (const pos of positions) {
          const price = priceMap[pos.ticker] ?? parseFloat(pos.cost_basis);
          const value = parseFloat(pos.quantity) * price;
          totalValue += value;
        }
        for (const pos of positions) {
          const price = priceMap[pos.ticker] ?? parseFloat(pos.cost_basis);
          weights.push((parseFloat(pos.quantity) * price) / totalValue);
        }

        // Get risk metrics from quant service
        let riskMetrics: any = {};
        try {
          const riskResult: any = await quantClient.portfolioRisk(tickers, weights);
          riskMetrics = riskResult?.data ?? {};
        } catch {
          errors.push(`Risk metrics failed for portfolio ${portfolio.id}`);
        }

        // Get yesterday's snapshot for day_return
        const { data: yesterday } = await admin
          .from("portfolio_snapshots")
          .select("total_value, target_probability")
          .eq("portfolio_id", portfolio.id)
          .order("date", { ascending: false })
          .limit(1);
        const prevValue = yesterday?.[0] ? parseFloat(yesterday[0].total_value) : totalValue;
        const dayReturn = prevValue > 0 ? (totalValue - prevValue) / prevValue : 0;

        // Simple health score
        const varScore = riskMetrics.var_95 ? Math.max(0, 35 * (1 - riskMetrics.var_95 * 10)) : 20;
        const divScore = Math.max(0, 40 * (1 - weights.reduce((a, w) => a + w * w, 0)));
        const healthScore = Math.min(100, Math.round(varScore + divScore + 25));

        // Risk level
        const var95 = riskMetrics.var_95 ?? 0.02;
        const riskLevel = var95 > 0.04 ? "high" : var95 > 0.025 ? "elevated" : var95 > 0.015 ? "moderate" : "low";

        // Sector exposure
        const { data: tickerData } = await admin
          .from("tickers")
          .select("symbol, sector")
          .in("symbol", tickers);
        const sectorExp: Record<string, number> = {};
        positions.forEach((pos: any, i: number) => {
          const sector = tickerData?.find((t: any) => t.symbol === pos.ticker)?.sector ?? "Unknown";
          sectorExp[sector] = (sectorExp[sector] ?? 0) + weights[i];
        });

        await admin.from("portfolio_snapshots").upsert({
          portfolio_id: portfolio.id,
          date: today,
          total_value: totalValue.toFixed(2),
          day_return: dayReturn,
          health_score: healthScore,
          diversification_score: divScore,
          risk_score: varScore,
          quality_score: 25,
          risk_level: riskLevel,
          exposures: { sector: sectorExp, geography: {}, theme: {}, hidden: [] },
          risk_metrics: riskMetrics,
          target_probability: 0.45,
          target_probability_delta: 0,
        }, { onConflict: "portfolio_id,date" });

        processed++;
      } catch (err) {
        errors.push(`Portfolio ${portfolio.id}: ${err instanceof Error ? err.message : String(err)}`);
      }
    }

    return jsonResponse({ processed, errors });
  } catch (err) {
    return errorResponse(err instanceof Error ? err.message : "Internal error", 500);
  }
});
