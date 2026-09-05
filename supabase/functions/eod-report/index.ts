// EOD report Edge Function — called by pg_cron at 18:00 ET.
// Diffs today vs yesterday, generates alerts, formats Telegram message.
import { corsHeaders, errorResponse, getSupabaseAdmin, jsonResponse } from "../_shared/auth.ts";
import { orchestratorClient } from "../_shared/service_clients.ts";

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders() });
  }

  const admin = getSupabaseAdmin();
  const today = new Date().toISOString().split("T")[0];
  let alertsCreated = 0;
  let usersProcessed = 0;

  try {
    // All users with notifications enabled
    const { data: profiles } = await admin
      .from("profiles")
      .select("user_id, target_cagr, horizon_years, telegram_chat_id, notifications_enabled")
      .eq("notifications_enabled", true);

    if (!profiles?.length) return jsonResponse({ users_processed: 0, alerts_created: 0 });

    for (const profile of profiles) {
      try {
        // Get primary portfolio
        const { data: portfolios } = await admin
          .from("portfolios")
          .select("id, name")
          .eq("user_id", profile.user_id)
          .limit(1);
        if (!portfolios?.length) continue;

        const portfolio = portfolios[0];

        // Get today's and yesterday's snapshots
        const { data: snapshots } = await admin
          .from("portfolio_snapshots")
          .select("*")
          .eq("portfolio_id", portfolio.id)
          .order("date", { ascending: false })
          .limit(2);

        const todaySnap = snapshots?.[0];
        const yesterdaySnap = snapshots?.[1];
        if (!todaySnap) continue;

        const dayRet = parseFloat(todaySnap.day_return ?? "0");
        const health = todaySnap.health_score ?? 0;
        const risk = todaySnap.risk_level ?? "moderate";
        const prob = todaySnap.target_probability ?? 0;
        const probDelta = yesterdaySnap ? prob - (yesterdaySnap.target_probability ?? 0) : 0;
        const targetCagr = profile.target_cagr * 100;
        const horizon = profile.horizon_years;

        // Material changes today
        const { data: changes } = await admin
          .from("portfolio_changes")
          .select("*")
          .eq("portfolio_id", portfolio.id)
          .eq("date", today)
          .order("created_at", { ascending: false })
          .limit(3);

        // Tomorrow's catalysts (positions tickers)
        const { data: positions } = await admin
          .from("positions")
          .select("ticker")
          .eq("portfolio_id", portfolio.id);
        const tickers = (positions ?? []).map((p: any) => p.ticker);

        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const tomorrowStr = tomorrow.toISOString().split("T")[0];

        const { data: catalysts } = await admin
          .from("catalysts")
          .select("*")
          .in("ticker", tickers)
          .eq("date", tomorrowStr);

        // Format Telegram message
        const sign = dayRet >= 0 ? "+" : "";
        const probSign = probDelta >= 0 ? "+" : "";
        let msg = `📊 DAILY PORTFOLIO BRIEF\n\n`;
        msg += `Portfolio: ${sign}${(dayRet * 100).toFixed(1)}%\n`;
        msg += `Health Score: ${health.toFixed(0)}/100\nRisk: ${risk.charAt(0).toUpperCase() + risk.slice(1)}\n\n`;
        msg += `🎯 ${horizon}-Year Objective\n`;
        msg += `Target CAGR: ${targetCagr.toFixed(0)}%\n`;
        msg += `Est. probability: ${(prob * 100).toFixed(0)}%  (${probSign}${(probDelta * 100).toFixed(0)}%)\n`;

        if (changes?.length) {
          msg += `\n⚠️ IMPORTANT\n`;
          changes.forEach((c: any) => { msg += `· ${c.summary}\n`; });
        }

        if (catalysts?.length) {
          msg += `\n📰 CATALYST\n`;
          catalysts.forEach((c: any) => { msg += `· ${c.ticker} — ${c.description} (${c.date})\n`; });
        }

        msg += `\nThis report is for research purposes only. Not investment advice.`;

        // Create alert record
        const alertTitle = `Portfolio ${sign}${(dayRet * 100).toFixed(1)}% · Health ${health.toFixed(0)}/100`;
        await admin.from("alerts").insert({
          user_id: profile.user_id,
          type: "news",
          tickers: tickers.slice(0, 5),
          title: alertTitle,
          body: msg.slice(0, 500),
          delivered_at: new Date().toISOString(),
        });
        alertsCreated++;

        // Send Telegram if configured
        if (profile.telegram_chat_id) {
          const botToken = Deno.env.get("TELEGRAM_BOT_TOKEN");
          if (botToken) {
            await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ chat_id: profile.telegram_chat_id, text: msg, parse_mode: "HTML" }),
            }).catch(() => {});
          }
        }

        usersProcessed++;
      } catch (err) {
        console.error(`EOD report failed for user ${profile.user_id}:`, err);
      }
    }

    return jsonResponse({ users_processed: usersProcessed, alerts_created: alertsCreated });
  } catch (err) {
    return errorResponse(err instanceof Error ? err.message : "Internal error", 500);
  }
});
