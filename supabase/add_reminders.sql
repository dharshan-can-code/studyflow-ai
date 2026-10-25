alter table public.students
    add column if not exists reminders jsonb not null default '{}'::jsonb;
