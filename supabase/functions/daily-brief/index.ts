import { corsHeaders } from '../_shared/cors.ts';
import { errorResponse, jsonResponse } from '../_shared/auth.ts';

// JWT auth is handled at the gateway level (verify_jwt: true).
Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const url = new URL(req.url);
    // portfolio_id comes from body (POST) or query string (GET)
    let portfolioId: string | null = url.searchParams.get('portfolio_id');
    let date: string | null = url.searchParams.get('date');

    if (req.method === 'POST') {
      const body = await req.json().catch(() => ({}));
      portfolioId = body.portfolio_id ?? portfolioId;
      date = body.date ?? date;
    }

    if (!portfolioId) {
      return errorResponse('portfolio_id is required', 400);
    }

    const orchestratorUrl = Deno.env.get('ORCHESTRATOR_URL');
    if (!orchestratorUrl) return errorResponse('ORCHESTRATOR_URL not configured', 503);

    const params = new URLSearchParams();
    if (date) params.set('date', date);
    const qs = params.toString() ? `?${params}` : '';

    const res = await fetch(`${orchestratorUrl}/brief/${portfolioId}${qs}`, {
      headers: { 'Content-Type': 'application/json' },
    });

    const data = await res.json();
    return jsonResponse(data, res.status);
  } catch (err) {
    return errorResponse(err instanceof Error ? err.message : 'Request failed');
  }
});
