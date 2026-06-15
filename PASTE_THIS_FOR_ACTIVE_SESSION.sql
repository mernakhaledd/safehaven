-- =====================================================================
-- Set Up Active Session Alert Routing
-- Paste this entire block into Supabase Dashboard -> SQL Editor -> Run
-- =====================================================================

-- 1. Create the active session tracking table
create table if not exists public.active_test_session (
  id integer primary key,
  user_id uuid references auth.users(id) on delete cascade,
  updated_at timestamptz not null default now()
);

-- Ensure a row exists (default to first registered profile owner if any)
insert into public.active_test_session (id, user_id)
values (1, (select user_id from public.profiles limit 1))
on conflict (id) do nothing;

-- Enable Row Level Security (RLS) on active session table
alter table public.active_test_session enable row level security;

drop policy if exists "active_test_session_unrestricted" on public.active_test_session;
create policy "active_test_session_unrestricted" on public.active_test_session
  for all using (true) with check (true);

-- 2. Define the routing trigger function
create or replace function public.auto_assign_alert_user_id()
returns trigger
language plpgsql
security definer
as $$
declare
  v_user_id uuid;
begin
  -- If user_id is already provided in the insert payload, use it
  if NEW.user_id is not null then
    return NEW;
  end if;

  -- A. Try matching by person_name against profiles
  if NEW.person_name is not null and lower(NEW.person_name) <> 'unknown' then
    select user_id into v_user_id
    from public.profiles
    where lower(display_name) = lower(NEW.person_name)
    limit 1;
  end if;

  -- B. Fallback: Route to the currently active test session user
  if v_user_id is null then
    select user_id into v_user_id
    from public.active_test_session
    where id = 1;
  end if;

  -- C. Last Fallback: get the user_id of the most recently created profile
  if v_user_id is null then
    select user_id into v_user_id
    from public.profiles
    order by created_at desc
    limit 1;
  end if;

  NEW.user_id := v_user_id;
  return NEW;
end;
$$;

-- Bind trigger to alerts table
drop trigger if exists alerts_auto_assign_user_id on public.alerts;
create trigger alerts_auto_assign_user_id
  before insert on public.alerts
  for each row execute function public.auto_assign_alert_user_id();

-- 3. Enable RLS on alerts to ensure accounts are securely segregated
alter table public.alerts enable row level security;

drop policy if exists "Allow Service/Anon Insert" on public.alerts;
drop policy if exists "Allow Authenticated Select" on public.alerts;
drop policy if exists "Allow Authenticated Update" on public.alerts;

create policy "Allow Service/Anon Insert"  on public.alerts for insert with check (true);
create policy "Allow Authenticated Select" on public.alerts for select using (user_id = auth.uid());
create policy "Allow Authenticated Update" on public.alerts for update using (user_id = auth.uid()) with check (user_id = auth.uid());
