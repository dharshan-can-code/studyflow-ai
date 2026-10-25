create extension if not exists pgcrypto;

create table if not exists public.students (
    id uuid primary key default gen_random_uuid(),
    google_sub text unique,
    guest_token_hash text unique,
    courses jsonb not null default '[]'::jsonb,
    activities jsonb not null default '[]'::jsonb,
    availability jsonb not null default '{}'::jsonb,
    assignments jsonb not null default '[]'::jsonb,
    study_plan jsonb,
    messages jsonb not null default '[]'::jsonb,
    profile jsonb not null default '{}'::jsonb,
    study_style jsonb not null default '{}'::jsonb,
    reminders jsonb not null default '{}'::jsonb,
    flashcards jsonb not null default '[]'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint students_have_identity check (
        google_sub is not null or guest_token_hash is not null
    )
);

alter table public.students enable row level security;

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.students to service_role;
