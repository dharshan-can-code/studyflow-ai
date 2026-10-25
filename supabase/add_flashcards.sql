alter table public.students
    add column if not exists flashcards jsonb not null default '[]'::jsonb;
