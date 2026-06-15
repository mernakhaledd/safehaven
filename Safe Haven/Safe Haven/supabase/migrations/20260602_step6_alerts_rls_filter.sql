-- =====================================================================
-- Safe Haven — STEP 6: Scoping Alerts by User Account
-- =====================================================================
-- Paste this entire file into Supabase Dashboard -> SQL Editor -> Run
-- Safe to re-run.
--
-- What this does:
--   1) Adds user_id column to public.alerts table referencing auth.users.
--   2) Replaces "Allow Authenticated Select" policy on public.alerts
--      so users can see alerts of their own account AND alerts of any
--      linked caregiver/receiver profiles on separate accounts.
--   3) Creates a database trigger to auto-assign user_id to incoming
--      alerts if it is NULL (matching person_name display name or fallback).
-- =====================================================================

alter table public.alerts add column if not exists user_id uuid references auth.users(id) on delete cascade;

drop policy if exists "Allow Authenticated Select" on public.alerts;

create policy "Allow Authenticated Select" on public.alerts
  for select using (
    user_id = auth.uid()
    or exists (
      select 1 from public.profile_links pl
      join public.profiles my_p on (my_p.id = pl.care_giver_profile_id or my_p.id = pl.care_receiver_profile_id)
      join public.profiles their_p on (their_p.id = pl.care_giver_profile_id or their_p.id = pl.care_receiver_profile_id)
      where my_p.user_id = auth.uid()
        and their_p.user_id = alerts.user_id
    )
  );

-- Trigger function to automatically resolve user_id when it is NULL
create or replace function public.auto_assign_alert_user_id()
returns trigger
language plpgsql
security definer
as $$
declare
  v_user_id uuid;
begin
  -- If user_id is already provided, keep it
  if NEW.user_id is not null then
    return NEW;
  end if;

  -- 1. Try matching by person_name against profiles
  if NEW.person_name is not null and lower(NEW.person_name) <> 'unknown' then
    select user_id into v_user_id
    from public.profiles
    where lower(display_name) = lower(NEW.person_name)
    limit 1;
  end if;

  -- 2. Fallback: get the user_id of the most recently created profile
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

drop trigger if exists alerts_auto_assign_user_id on public.alerts;
create trigger alerts_auto_assign_user_id
  before insert on public.alerts
  for each row execute function public.auto_assign_alert_user_id();
