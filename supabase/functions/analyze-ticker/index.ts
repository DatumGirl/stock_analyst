import { corsHeaders } from '../_shared/cors.ts';
import { errorResponse, jsonResponse } from '../_shared/auth.ts';

// JWT auth is handled at the gateway level (verify_jwt: true).
Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const body = await req.json();
    const orchestratorUrl = Deno.env.get('ORCHESTRATOR_URL');
    if (!orchestratorUrl) return errorResponse('ORCHESTRATOR_URL not configured', 503);

    const res = await fetch(`${orchestratorUrl}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return jsonResponse(data, res.status);
  } catch (err) {
    return errorResponse(err instanceof Error ? err.message : 'Request failed');
  }
});
