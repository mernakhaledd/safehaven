-- Create alerts table for Raspberry Pi Integration
create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  type text not null, -- 'FALL' or 'HELP_GESTURE'
  confidence numeric not null,
  status text not null default 'new', -- 'new', 'read', 'resolved'
  created_at timestamptz not null default now()
);

-- Enable RLS (Row Level Security)
alter table public.alerts enable row level security;

-- Allow anyone (anon) to INSERT alerts (so Pi can write without complex auth for now)
-- In production, you would use a service_role key, but for this demo, anon with a policy is easiest.
create policy "Allow Service/Anon Insert" on public.alerts
  for insert with check (true);

-- Allow authenticated users (Mobile App) to SELECT alerts
create policy "Allow Authenticated Select" on public.alerts
  for select using (auth.role() = 'authenticated');

-- Realtime subscription is enabled by default on new tables in Supabase, 
-- but ensuring replication is on allows the app to get instant updates.
alter publication supabase_realtime add table public.alerts;
