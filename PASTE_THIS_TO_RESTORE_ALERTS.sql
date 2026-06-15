-- =====================================================================
-- Restore Legacy Alerts — Disable RLS & Remove Account Restrictions
-- Paste this block into Supabase Dashboard -> SQL Editor -> Run
-- =====================================================================

-- 1. Disable Row Level Security on alerts table completely
alter table public.alerts disable row level security;

-- 2. Drop all alert filters and access policies
drop policy if exists "Allow Service/Anon Insert" on public.alerts;
drop policy if exists "Allow Authenticated Select" on public.alerts;
drop policy if exists "Allow Authenticated Update" on public.alerts;

-- 3. Remove the automatic user ID assignment trigger
drop trigger if exists alerts_auto_assign_user_id on public.alerts;
drop function if exists public.auto_assign_alert_user_id();

-- 4. Re-ensure alerts table is in the realtime publication
do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='alerts') then
    alter publication supabase_realtime add table public.alerts;
  end if;
end $$;
