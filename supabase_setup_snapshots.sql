-- ============================================================
-- SafeHaven: Snapshot feature
--   1) auto-photo of unknown person attached to its alert
--   2) on-demand "photo of care receiver" requests
-- Paste this WHOLE file into Supabase Dashboard -> SQL Editor -> Run.
-- Safe to run more than once.
-- ============================================================

-- 1. Alerts can now carry a photo --------------------------------------------
alter table public.alerts add column if not exists photo_url text;

-- 2. Private bucket to hold captured photos ----------------------------------
insert into storage.buckets (id, name, public)
values ('snapshots', 'snapshots', false)
on conflict (id) do nothing;

-- Authenticated users may read their own household's snapshots
-- (the Pi uploads with the service key, which bypasses these rules).
drop policy if exists snaps_read on storage.objects;
create policy snaps_read on storage.objects for select to authenticated
  using (bucket_id = 'snapshots'
         and ((storage.foldername(name))[1])::uuid in (select public.my_households()));

-- 3. On-demand photo requests ------------------------------------------------
create table if not exists public.photo_requests (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references public.households(id) on delete cascade,
  requested_by uuid references auth.users(id),
  status text not null default 'pending',   -- pending | done
  photo_url text,
  created_at timestamptz default now()
);

alter table public.photo_requests enable row level security;

drop policy if exists pr_select on public.photo_requests;
drop policy if exists pr_insert on public.photo_requests;

create policy pr_select on public.photo_requests for select to authenticated
  using (household_id in (select public.my_households()));
create policy pr_insert on public.photo_requests for insert to authenticated
  with check (household_id in (select public.my_households()));

-- make sure the app gets realtime updates for fulfilled requests
do $$ begin
  if not exists (select 1 from pg_publication_tables
    where pubname='supabase_realtime' and schemaname='public' and tablename='photo_requests') then
    alter publication supabase_realtime add table public.photo_requests;
  end if;
end $$;
