-- Starts the "Send study reminders" GitHub workflow every 10 minutes, on time.
-- GitHub's own schedule often runs hours late, so this makes reminders arrive when students asked.
--
-- Before running this file:
-- 1. Make a GitHub fine-grained token for this repository with "Actions: Read and write".
-- 2. Replace PASTE_GITHUB_TOKEN_HERE below with it (it is stored encrypted in Supabase Vault).
-- 3. If your repository is not dharshan-can-code/studyflow-ai, change the URL below.

create extension if not exists pg_cron;
create extension if not exists pg_net;

select vault.create_secret('PASTE_GITHUB_TOKEN_HERE', 'studyflow_github_token')
where not exists (select 1 from vault.secrets where name = 'studyflow_github_token');

select cron.unschedule('studyflow-reminders')
where exists (select 1 from cron.job where jobname = 'studyflow-reminders');

select cron.schedule(
    'studyflow-reminders',
    '*/10 * * * *',
    $$
    select net.http_post(
        url := 'https://api.github.com/repos/dharshan-can-code/studyflow-ai/actions/workflows/reminders.yml/dispatches',
        headers := jsonb_build_object(
            'Authorization', 'Bearer ' || (
                select decrypted_secret from vault.decrypted_secrets where name = 'studyflow_github_token'
            ),
            'Accept', 'application/vnd.github+json',
            'Content-Type', 'application/json',
            'User-Agent', 'studyflow-reminders'
        ),
        body := '{"ref": "main"}'::jsonb
    );
    $$
);
