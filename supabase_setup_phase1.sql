-- ============================================================
-- SafeHaven Phase 1: dynamic face enrollment tables
-- Paste this WHOLE file into Supabase Dashboard -> SQL Editor -> Run
-- Safe to run more than once.
-- ============================================================

-- 1. Households -----------------------------------------------------
create table if not exists households (
  id uuid primary key default gen_random_uuid(),
  name text not null default 'My Home',
  owner_id uuid not null references auth.users(id),
  created_at timestamptz default now()
);

create table if not exists household_members (
  household_id uuid references households(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  role text not null default 'owner',
  primary key (household_id, user_id)
);

-- 2. People to recognize --------------------------------------------
create table if not exists family_members (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references households(id) on delete cascade,
  display_name text not null,
  created_by uuid references auth.users(id),
  created_at timestamptz default now()
);

create table if not exists member_photos (
  id uuid primary key default gen_random_uuid(),
  member_id uuid not null references family_members(id) on delete cascade,
  storage_path text not null,
  status text not null default 'pending',   -- pending | processed | rejected
  reject_reason text,
  created_at timestamptz default now()
);

create table if not exists face_embeddings (
  id uuid primary key default gen_random_uuid(),
  member_id uuid not null references family_members(id) on delete cascade,
  household_id uuid not null references households(id) on delete cascade,
  photo_id uuid references member_photos(id) on delete cascade,
  embedding float8[] not null,
  model_version text not null default 'sface_2021dec',
  created_at timestamptz default now()
);

-- 3. Permissive security for Phase 1 ---------------------------------
-- (Phase 2 will replace these with strict per-household policies)
alter table households enable row level security;
alter table household_members enable row level security;
alter table family_members enable row level security;
alter table member_photos enable row level security;
alter table face_embeddings enable row level security;

drop policy if exists p1_households on households;
create policy p1_households on households
  for all to anon, authenticated using (true) with check (true);

drop policy if exists p1_household_members on household_members;
create policy p1_household_members on household_members
  for all to anon, authenticated using (true) with check (true);

drop policy if exists p1_family_members on family_members;
create policy p1_family_members on family_members
  for all to anon, authenticated using (true) with check (true);

drop policy if exists p1_member_photos on member_photos;
create policy p1_member_photos on member_photos
  for all to anon, authenticated using (true) with check (true);

drop policy if exists p1_face_embeddings on face_embeddings;
create policy p1_face_embeddings on face_embeddings
  for all to anon, authenticated using (true) with check (true);

-- 4. Storage bucket for face photos ----------------------------------
insert into storage.buckets (id, name, public)
values ('faces', 'faces', false)
on conflict (id) do nothing;

drop policy if exists p1_faces_storage on storage.objects;
create policy p1_faces_storage on storage.objects
  for all to anon, authenticated
  using (bucket_id = 'faces') with check (bucket_id = 'faces');
