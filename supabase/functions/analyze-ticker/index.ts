import { AuthError, corsHeaders, errorResponse, getSupabaseAdmin, jsonResponse, requireAuth } from "../_shared/auth.ts";
import { orchestratorClient } from "../_shared/service_clients.ts";

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders() });
  }

  try {
    const userId = await requireAuth(req);
    const { ticker, portfolio_id } = await req.json();

    if (!ticker || typeof ticker !== "string") {
      return errorResponse("ticker is required");
    }
    const sym = ticker.toUpperCase().trim();
    if (!/^[A-Z0-9.^=-]{1,7}$/.test(sym)) {
      return errorResponse(`Invalid ticker: ${ticker}`);
    }

    // Verify portfolio belongs to user if provided
    if (portfolio_id) {
      const admin = getSupabaseAdmin();
      const { data, error } = await admin
        .from("portfolios")
        .select("id")
        .eq("id", portfolio_id)
        .eq("user_id", userId)
        .single();
      if (error || !data) {
        return errorResponse("Portfolio not found or access denied", 403);
      }
    }

    const token = req.headers.get("Authorization")?.slice(7);
    const result = await orchestratorClient.analyzeTicker(sym, portfolio_id, token);

    // Log analysis run
    const admin = getSupabaseAdmin();
    await admin.from("analysis_runs").insert({
      user_id: userId,
      ticker: sym,
      run_type: "analyze",
      model_version: "claude-opus-4-8",
      created_at: new Date().toISOString(),
    });

    return jsonResponse(result);
  } catch (err) {
    if (err instanceof AuthError) return errorResponse(err.message, 401);
    console.error("analyze-ticker error:", err);
    return errorResponse(err instanceof Error ? err.message : "Internal error", 500);
  }
});
