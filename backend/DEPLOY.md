# Put Savoré online (Supabase database + Render server)

Both are free. You do these steps yourself because they need your accounts and passwords.
Total time: about 30 minutes (most of it waiting for the product import).

```
Phone app  ──►  Render (runs the API)  ──►  Supabase (PostgreSQL database)
```

## 1. Database on Supabase

1. Sign up at **supabase.com** → **New project**. Name `savore`, pick a region near you (Mumbai if shown),
   and set a **database password**. Write it down (you can't see it again).
2. Wait about 2 minutes until the project is ready.
3. Click **Connect** (top of the page) → **Session pooler** → copy the connection string.
   It looks like `postgresql://postgres.abcdefgh:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`
4. Replace `[YOUR-PASSWORD]` with your password. If the password contains symbols like `@ # / :`, change the
   password to letters and numbers only, to avoid trouble.

> Use **Session pooler**, not "Direct connection". Render's free servers only understand IPv4, and Supabase's
> direct connection is IPv6 only.

## 2. Fill the database with products (from your PC)

Open PowerShell in the `backend` folder (keep your password out of chats and out of git):

```powershell
$env:DATABASE_URL = "PASTE-THE-CONNECTION-STRING-HERE"
.venv\Scripts\python -m scripts.import_off --limit 5000
```

- It creates the tables, adds the 8 sample products, then imports up to **5,000 real Indian products** from
  Open Food Facts. This takes about 10 to 20 minutes because Open Food Facts limits how fast you can ask.
- If it stops (internet, or Open Food Facts is busy), run the same command again with
  `--start-page N` (it prints N at the end). Products already added are skipped.
- Check it worked: Supabase → **Table Editor** → `products`.

**Faster alternative:** if your local `savore.db` already has products, copy it instead (takes seconds; it
refuses to touch a database that already has products):

```powershell
$env:DATABASE_URL = "PASTE-THE-CONNECTION-STRING-HERE"
.venv\Scripts\python -m scripts.copy_db
```

**Then lock the tables:** in Supabase → **SQL Editor**, run `ALTER TABLE public.<name> ENABLE ROW LEVEL SECURITY;`
for each table (or let Claude do it). Our server connects as the table owner, so it keeps working, and nobody can
read or edit the data through Supabase's public API.

## 3. Put the code on GitHub

Install Git if needed, create an empty repository on github.com (private is fine), then in the project
folder (`C:\PRJ`):

```bash
git init
git add .
git commit -m "Savore app and backend"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/YOUR-REPO.git
git push -u origin main
```

(`.gitignore` already keeps your database file, virtual environment and passwords out.)

## 4. Run the API on Render

0. If your repository is **private**, Render must be allowed to read it first: Render → your name (top right) →
   **Account Settings** → **GitHub** → connect, and give it access to the `Savore` repository.
1. Sign up at **render.com** → **New +** → **Blueprint** → connect GitHub → pick your repository.
   Render reads `render.yaml` and proposes a web service called `savore-api`.
2. It asks for **DATABASE_URL**: paste the Supabase connection string from step 1.
3. **Apply**. The first deploy takes 3 to 5 minutes.
4. Open `https://savore-api.onrender.com/health` (your service URL is shown at the top of the Render page).
   You should see `{"status":"ok","products":5008}`. `/docs` shows every endpoint.
5. The reviewer password was generated for you: Render → your service → **Environment** → `REVIEWER_KEY`.

## 5. Point the app at it

Run on your phone:

```bash
flutter run --dart-define=API_URL=https://savore-api.onrender.com
```

or build an APK to install or share:

```bash
flutter build apk --release --dart-define=API_URL=https://savore-api.onrender.com
```

The APK is `build\app\outputs\flutter-apk\app-release.apk`.

## Things to know before the demo

- **Render's free server falls asleep after 15 minutes without use.** The next request takes 30 to 60 seconds
  to wake it (the app waits up to 60 seconds). **Open `/health` in a browser a few minutes before you present.**
- Supabase's free database is paused after 1 week with no activity. Open the Supabase dashboard and click
  **Restore** if that happens.
- If the app says it can't reach the server, check `/health` in a browser first. If that works, check that the
  `API_URL` you built the app with is spelled exactly the same.
- Never put the Supabase password in the app, in GitHub, or in a chat. It only belongs in Render's
  environment settings and in your own terminal.
