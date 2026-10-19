alter table public.students
    add column if not exists profile jsonb not null default '{}'::jsonb;

alter table public.students
    add column if not exists study_style jsonb not null default '{}'::jsonb;
