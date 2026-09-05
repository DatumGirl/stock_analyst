// Pre-market brief — called by pg_cron at 05:30 ET (09:30 UTC).
import { corsHeaders, errorResponse, getSupabaseAdmin, jsonResponse } from "../_shared/auth.ts";

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders() });
  }

  const admin = getSupabaseAdmin();
  const today = new Date().toISOString().split("T")[0];
  let alertsCreated = 0;

  try {
    const { data: profiles } = await admin
      .from("profiles")
      .select("user_id, telegram_chat_id, notifications_enabled")
      .eq("notifications_enabled", true);

    if (!profiles?.length) return jsonResponse({ alerts_created: 0 });

    // Overnight news (last 12 hours, materiality > 0.5)
    const twelveHoursAgo = new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString();
    const { data: overnightNews } = await admin
      .from("news_events")
      .select("*")
      .gte("as_of", twelveHoursAgo)
      .gte("materiality_score", 0.5)
      .order("materiality_score", { ascending: false })
      .limit(20);

    // Today's catalysts (earnings, macro events)
    const { data: todayCatalysts } = await admin
      .from("catalysts")
      .select("*")
      .eq("date", today)
      .order("type");

    for (const profile of profiles) {
      try {
        // Get user's tickers (portfolio + watchlist)
        const { data: portfolios } = await admin
          .from("portfolios")
          .select("id")
          .eq("user_id", profile.user_id)
          .limit(1);

        const userTickers = new Set<string>();
        if (portfolios?.[0]) {
          const { data: positions } = await admin
            .from("positions")
            .select("ticker")
            .eq("portfolio_id", portfolios[0].id);
          positions?.forEach((p: any) => userTickers.add(p.ticker));
        }

        // Filter news relevant to user's tickers
        const relevantNews = (overnightNews ?? []).filter((n: any) =>
          n.tickers?.some((t: string) => userTickers.has(t))
        );

        // Filter catalysts for user's tickers
        const relevantCatalysts = (todayCatalysts ?? []).filter((c: any) =>
          userTickers.has(c.ticker)
        );

        if (!relevantNews.length && !relevantCatalysts.length) continue;

        let summary = "";
        if (relevantCatalysts.length) {
          summary += `Today's catalysts: ${relevantCatalysts.map((c: any) => `${c.ticker} (${c.type})`).join(", ")}. `;
        }
        if (relevantNews.length) {
          summary += `${relevantNews.length} material news item(s) overnight.`;
        }

        await admin.from("alerts").insert({
          user_id: profile.user_id,
          type: "news",
          tickers: Array.from(userTickers).slice(0, 10),
          title: "Pre-market brief ready",
          body: summary,
          delivered_at: new Date().toISOString(),
        });
        alertsCreated++;

        // Telegram pre-market summary
        if (profile.telegram_chat_id && relevantCatalysts.length) {
          const botToken = Deno.env.get("TELEGRAM_BOT_TOKEN");
          if (botToken) {
            const msg = `🌅 PRE-MARKET BRIEF\n\n📅 Today's catalysts:\n` +
              relevantCatalysts.map((c: any) => `· ${c.ticker} — ${c.description}`).join("\n") +
              (relevantNews.length ? `\n\n📰 ${relevantNews.length} material overnight news items.` : "");
            await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ chat_id: profile.telegram_chat_id, text: msg }),
            }).catch(() => {});
          }
        }
      } catch (err) {
        console.error(`Pre-market failed for user ${profile.user_id}:`, err);
      }
    }

    return jsonResponse({ alerts_created: alertsCreated });
  } catch (err) {
    return errorResponse(err instanceof Error ? err.message : "Internal error", 500);
  }
});
