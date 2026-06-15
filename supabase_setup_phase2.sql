-- ============================================================
-- SafeHaven Phase 2: strict per-household security (RLS)
--
-- IMPORTANT: before running this, make sure the Raspberry Pi is using the
-- SERVICE ROLE key (see the chat steps). The service key bypasses these
-- rules, so the Pi keeps working. The mobile app uses the anon key + each
-- user's login, so it becomes locked to its own household only.
--
-- Paste this WHOLE file into Supabase Dashboard -> SQL Editor -> Run.
-- Safe to run more than once.
-- ============================================================

-- Helper: the set of household ids the logged-in user belongs to ----------
create or replace function public.my_households()
returns setof uuid
language sql
security definer
stable
as $$
  select household_id from public.household_members where user_id = auth.uid()
  union
  select id from public.households where owner_id = auth.uid()
$$;

-- 1. households -----------------------------------------------------------
alter table public.households enable row level security;
drop policy if exists p1_households on public.households;
drop policy if exists hh_select on public.households;
drop policy if exists hh_insert on public.households;
drop policy if exists hh_update on public.households;
drop policy if exists hh_delete on public.households;

create policy hh_select on public.households for select to authenticated
  using (id in (select public.my_households()));
create policy hh_insert on public.households for insert to authenticated
  with check (owner_id = auth.uid());
create policy hh_update on public.households for update to authenticated
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy hh_delete on public.households for delete to authenticated
  using (owner_id = auth.uid());

-- 2. household_members ----------------------------------------------------
alter table public.household_members enable row level security;
drop policy if exists p1_household_members on public.household_members;
drop policy if exists hm_select on public.household_members;
drop policy if exists hm_insert on public.household_members;
drop policy if exists hm_delete on public.household_members;

create policy hm_select on public.household_members for select to authenticated
  using (user_id = auth.uid()
         or household_id in (select id from public.households where owner_id = auth.uid()));
create policy hm_insert on public.household_members for insert to authenticated
  with check (user_id = auth.uid()
              or household_id in (select id from public.households where owner_id = auth.uid()));
create policy hm_delete on public.household_members for delete to authenticated
  using (household_id in (select id from public.households where owner_id = auth.uid()));

-- 3. family_members -------------------------------------------------------
alter table public.family_members enable row level security;
drop policy if exists p1_family_members on public.family_members;
drop policy if exists fm_all on public.family_members;

create policy fm_all on public.family_members for all to authenticated
  using (household_id in (select public.my_households()))
  with check (household_id in (select public.my_households()));

-- 4. member_photos --------------------------------------------------------
alter table public.member_photos enable row level security;
drop policy if exists p1_member_photos on public.member_photos;
drop policy if exists mp_all on public.member_photos;

create policy mp_all on public.member_photos for all to authenticated
  using (member_id in (select id from public.family_members
                       where household_id in (select public.my_households())))
  with check (member_id in (select id from public.family_members
                            where household_id in (select public.my_households())));

-- 5. face_embeddings ------------------------------------------------------
alter table public.face_embeddings enable row level security;
drop policy if exists p1_face_embeddings on public.face_embeddings;
drop policy if exists fe_all on public.face_embeddings;

create policy fe_all on public.face_embeddings for all to authenticated
  using (household_id in (select public.my_households()))
  with check (household_id in (select public.my_households()));

-- 6. Storage bucket "faces": each account only its own household folder ----
drop policy if exists p1_faces_storage on storage.objects;
drop policy if exists faces_rw on storage.objects;

create policy faces_rw on storage.objects for all to authenticated
  using (bucket_id = 'faces'
         and ((storage.foldername(name))[1])::uuid in (select public.my_households()))
  with check (bucket_id = 'faces'
              and ((storage.foldername(name))[1])::uuid in (select public.my_households()));

-- Note: the alerts table keeps its existing rules (each account sees only
-- alerts where user_id = its own id), which already work correctly.
