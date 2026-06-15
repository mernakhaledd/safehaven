// Supabase Edge Function: send_push
// Sends push notifications to Expo tokens stored in `device_push_tokens`.
//
// Deploy:
// - supabase functions deploy send_push --project-ref <ref>
// Invoke:
// - supabase functions invoke send_push --project-ref <ref> --body '{"user_id":"...","title":"...","body":"..."}'

import { createClient } from "jsr:@supabase/supabase-js@2";

type Req = {
  user_id: string;
  title: string;
  body: string;
  data?: Record<string, unknown>;
  to_profile_id?: string;
};

Deno.serve(async (request) => {
  if (request.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

  const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey);

  const payload = (await request.json()) as Req;
  if (!payload?.user_id || !payload?.title || !payload?.body) {
    return new Response("Missing required fields", { status: 400 });
  }

  let query = supabaseAdmin
    .from("device_push_tokens")
    .select("expo_push_token")
    .eq("user_id", payload.user_id);

  if (payload.to_profile_id) {
    query = query.eq("profile_id", payload.to_profile_id);
  }

  const { data, error } = await query;
  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { "content-type": "application/json" },
    });
  }

  const tokens = (data ?? []).map((r) => r.expo_push_token).filter(Boolean);
  if (tokens.length === 0) {
    return new Response(JSON.stringify({ ok: true, sent: 0 }), {
      headers: { "content-type": "application/json" },
    });
  }

  const messages = tokens.map((to) => ({
    to,
    sound: "default",
    title: payload.title,
    body: payload.body,
    data: payload.data ?? {},
  }));

  const expoRes = await fetch("https://exp.host/--/api/v2/push/send", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json",
    },
    body: JSON.stringify(messages),
  });

  const result = await expoRes.json();
  return new Response(JSON.stringify({ ok: true, sent: tokens.length, result }), {
    headers: { "content-type": "application/json" },
  });
});

