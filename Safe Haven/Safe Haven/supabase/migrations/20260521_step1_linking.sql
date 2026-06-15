-- =====================================================================
-- Safe Haven — STEP 1: Cross-user linking
-- =====================================================================
-- Paste this entire file into Supabase Dashboard -> SQL Editor -> Run.
-- Safe to re-run.
--
-- What this does:
--   1) Lets profile_links join profiles owned by DIFFERENT users
--      (previously both profiles had to belong to the same auth user).
--   2) Adds a link_requests table so a caregiver can invite a receiver
--      by email, and the receiver can Accept / Decline.
--   3) Adds an accept_link_request() RPC that securely creates the link.
--   4) Adds the new tables to the Realtime publication so the UI updates
--      live when a request lands or is accepted.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Loosen profile_links: drop the same-user constraint
-- ---------------------------------------------------------------------

-- IMPORTANT order: drop the policy that references user_id BEFORE
-- dropping the column itself, otherwise Postgres rejects the change.
drop policy if exists profile_links_crud_own on public.profile_links;

-- Now it is safe to drop the old "user_id" column (it forced same-user links).
alter table public.profile_links drop column if exists user_id;

drop policy if exists profile_links_select on public.profile_links;
create policy profile_links_select on public.profile_links
  for select using (
    exists (
      select 1 from public.profiles p
      where p.id = care_giver_profile_id and p.user_id = auth.uid()
    )
    or exists (
      select 1 from public.profiles p
      where p.id = care_receiver_profile_id and p.user_id = auth.uid()
    )
  );

drop policy if exists profile_links_delete on public.profile_links;
create policy profile_links_delete on public.profile_links
  for delete using (
    exists (
      select 1 from public.profiles p
      where p.id = care_giver_profile_id and p.user_id = auth.uid()
    )
    or exists (
      select 1 from public.profiles p
      where p.id = care_receiver_profile_id and p.user_id = auth.uid()
    )
  );

-- NOTE: no INSERT policy on profile_links. New links are only created
-- through accept_link_request() (SECURITY DEFINER) below.

-- ---------------------------------------------------------------------
-- 2. link_requests table
-- ---------------------------------------------------------------------
create table if not exists public.link_requests (
  id uuid primary key default gen_random_uuid(),
  from_user_id uuid not null references auth.users(id) on delete cascade,
  from_profile_id uuid not null references public.profiles(id) on delete cascade,
  from_display_name text not null,
  to_email text not null,
  status text not null default 'pending',  -- 'pending' | 'accepted' | 'declined' | 'cancelled'
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists link_requests_to_email_idx
  on public.link_requests (lower(to_email));
create index if not exists link_requests_from_user_id_idx
  on public.link_requests (from_user_id);
create index if not exists link_requests_status_idx
  on public.link_requests (status);

-- updated_at trigger
do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'link_requests_set_updated_at') then
    create trigger link_requests_set_updated_at before update on public.link_requests
      for each row execute function public.set_updated_at();
  end if;
end $$;

-- RLS
alter table public.link_requests enable row level security;

drop policy if exists link_requests_select on public.link_requests;
create policy link_requests_select on public.link_requests
  for select using (
    from_user_id = auth.uid()
    or lower(to_email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );

drop policy if exists link_requests_insert on public.link_requests;
create policy link_requests_insert on public.link_requests
  for insert with check (
    from_user_id = auth.uid()
    and exists (
      select 1 from public.profiles p
      where p.id = from_profile_id
        and p.user_id = auth.uid()
        and p.persona = 'care_giver'
    )
  );

drop policy if exists link_requests_update on public.link_requests;
create policy link_requests_update on public.link_requests
  for update using (
    from_user_id = auth.uid()
    or lower(to_email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  ) with check (
    from_user_id = auth.uid()
    or lower(to_email) = lower(coalesce(auth.jwt() ->> 'email', ''))
  );

drop policy if exists link_requests_delete on public.link_requests;
create policy link_requests_delete on public.link_requests
  for delete using (from_user_id = auth.uid());

-- ---------------------------------------------------------------------
-- 3. accept_link_request RPC
-- ---------------------------------------------------------------------
-- The receiver calls this with the request id and which of their
-- care_receiver profiles to link. Runs as SECURITY DEFINER so it can
-- insert into profile_links even though that table has no INSERT policy.
create or replace function public.accept_link_request(
  p_request_id uuid,
  p_receiver_profile_id uuid
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_request public.link_requests%rowtype;
  v_link_id uuid;
  v_caller_email text;
begin
  v_caller_email := lower(coalesce(auth.jwt() ->> 'email', ''));

  select * into v_request from public.link_requests where id = p_request_id;
  if not found then
    raise exception 'Link request not found';
  end if;
  if v_request.status <> 'pending' then
    raise exception 'Link request is not pending';
  end if;
  if lower(v_request.to_email) <> v_caller_email then
    raise exception 'You are not the recipient of this request';
  end if;

  if not exists (
    select 1 from public.profiles p
    where p.id = p_receiver_profile_id
      and p.user_id = auth.uid()
      and p.persona = 'care_receiver'
  ) then
    raise exception 'Selected profile is not a care receiver profile owned by you';
  end if;

  insert into public.profile_links (care_giver_profile_id, care_receiver_profile_id)
  values (v_request.from_profile_id, p_receiver_profile_id)
  on conflict (care_giver_profile_id, care_receiver_profile_id) do nothing
  returning id into v_link_id;

  update public.link_requests
     set status = 'accepted'
   where id = p_request_id;

  return v_link_id;
end;
$$;

grant execute on function public.accept_link_request(uuid, uuid) to authenticated;

-- decline_link_request RPC (simpler — just marks status)
create or replace function public.decline_link_request(p_request_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_caller_email text;
  v_to_email text;
begin
  v_caller_email := lower(coalesce(auth.jwt() ->> 'email', ''));

  select to_email into v_to_email from public.link_requests where id = p_request_id;
  if v_to_email is null then
    raise exception 'Link request not found';
  end if;
  if lower(v_to_email) <> v_caller_email then
    raise exception 'You are not the recipient of this request';
  end if;

  update public.link_requests
     set status = 'declined'
   where id = p_request_id and status = 'pending';
end;
$$;

grant execute on function public.decline_link_request(uuid) to authenticated;

-- ---------------------------------------------------------------------
-- 4. Realtime publication for link_requests and profile_links
-- ---------------------------------------------------------------------
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'link_requests'
  ) then
    alter publication supabase_realtime add table public.link_requests;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'profile_links'
  ) then
    alter publication supabase_realtime add table public.profile_links;
  end if;
end $$;

-- =====================================================================
-- Verify in Dashboard -> Table Editor:
--   * link_requests should exist
--   * profile_links should no longer have a user_id column
-- And under Database -> Functions:
--   * accept_link_request and decline_link_request should be listed.
-- =====================================================================
