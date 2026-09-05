import { corsHeaders } from '../_shared/cors.ts';
import { errorResponse, jsonResponse } from '../_shared/auth.ts';

const BOT_TOKEN = Deno.env.get('TELEGRAM_BOT_TOKEN');
const CHAT_ID = Deno.env.get('TELEGRAM_CHAT_ID');

interface BriefData {
  portfolio_return: number;
  health_score: number;
  risk_level: string;
  target_probability: number;
  target_probability_delta: number;
  important: Array<{ description?: string; ticker?: string; change?: string }>;
  catalysts: Array<{ ticker?: string; description?: string; type?: string; date?: string }>;
  opportunities: Array<{ ticker: string; score: number; action: string }>;
  action_plan: Array<{ ticker: string; action: string; reason?: string }>;
  rebalance_required: boolean;
}

function sign(n: number): string {
  return n >= 0 ? '+' : '';
}

function formatBrief(d: BriefData): string {
  const returnPct = `${sign(d.portfolio_return)}${(d.portfolio_return * 100).toFixed(1)}%`;
  const probPct = `${(d.target_probability * 100).toFixed(0)}%`;
  const deltaPct = d.target_probability_delta !== 0
    ? ` (${sign(d.target_probability_delta)}${(d.target_probability_delta * 100).toFixed(1)}%)`
    : '';

  let msg = `📊 *DAILY PORTFOLIO BRIEF*\n\n`;
  msg += `Portfolio: ${returnPct}\n`;
  msg += `Health Score: ${d.health_score}/100\n`;
  msg += `Risk: ${d.risk_level}\n\n`;
  msg += `🎯 *Target Probability*\n`;
  msg += `${probPct}${deltaPct}\n`;

  if (d.important?.length > 0) {
    msg += `\n⚠️ *IMPORTANT*\n`;
    for (const item of d.important.slice(0, 3)) {
      const text = item.description ?? item.change ?? JSON.stringify(item);
      msg += `• ${text}\n`;
    }
  }

  if (d.catalysts?.length > 0) {
    msg += `\n📰 *CATALYSTS*\n`;
    for (const cat of d.catalysts.slice(0, 3)) {
      const label = cat.description ?? cat.type ?? 'Event';
      const ticker = cat.ticker ? `${cat.ticker} — ` : '';
      const date = cat.date ? ` (${cat.date})` : '';
      msg += `• ${ticker}${label}${date}\n`;
    }
  }

  if (d.opportunities?.length > 0) {
    msg += `\n📈 *OPPORTUNITIES*\n`;
    for (const opp of d.opportunities.slice(0, 5)) {
      msg += `${opp.ticker.padEnd(6)} ${opp.score}/100\n`;
    }
  }

  if (d.action_plan?.length > 0) {
    msg += `\n🔎 *TOMORROW*\n`;
    for (const item of d.action_plan.slice(0, 6)) {
      msg += `${item.ticker} — ${item.action}\n`;
    }
  }

  msg += `\n${d.rebalance_required ? '⚠️ Portfolio rebalance recommended.' : 'No portfolio rebalance required.'}\n`;
  return msg;
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    if (!BOT_TOKEN || !CHAT_ID) {
      return errorResponse('TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured in Edge Function secrets', 503);
    }

    const body = await req.json().catch(() => ({})) as Record<string, string>;
    const portfolioId = body.portfolio_id;
    if (!portfolioId) {
      return errorResponse('portfolio_id is required', 400);
    }

    const orchestratorUrl = Deno.env.get('ORCHESTRATOR_URL');
    if (!orchestratorUrl) return errorResponse('ORCHESTRATOR_URL not configured', 503);

    const briefRes = await fetch(`${orchestratorUrl}/brief/${portfolioId}`);
    if (!briefRes.ok) {
      return errorResponse(`Brief fetch failed: HTTP ${briefRes.status}`, 502);
    }
    const envelope = await briefRes.json();
    const briefData: BriefData = envelope.data ?? envelope;

    const text = formatBrief(briefData);

    const tgRes = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: CHAT_ID,
        text,
        parse_mode: 'Markdown',
      }),
    });

    const tgData = await tgRes.json() as { ok: boolean; result?: { message_id: number }; description?: string };
    if (!tgData.ok) {
      return errorResponse(`Telegram API error: ${tgData.description ?? 'unknown'}`, 502);
    }

    return jsonResponse({ sent: true, message_id: tgData.result?.message_id, chat_id: CHAT_ID });
  } catch (err) {
    return errorResponse(err instanceof Error ? err.message : 'Request failed');
  }
});
