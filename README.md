# studyflow-ai
Github repository for StudyflowAI app

## Project structure

```
app.py                  Streamlit app (run with: streamlit run app.py)
send_reminders.py       Daily reminder emails, run by the GitHub Action
requirements.txt

studyflow/
    planning/           scheduler, FCPS A/B day calendar, analytics
    data/               Supabase storage, file uploads, FCPS course list
    ui/                 setup forms, flashcards, glass background
    exports/            calendar (.ics) export, reminder emails

assets/
    images/             favicon and logo
    styles/             app.css, glass.css
    scripts/            glass background script and shaders

supabase/               database SQL
.github/workflows/      reminder email schedule
```
