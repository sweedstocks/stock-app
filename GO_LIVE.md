# Turn your stock alerts into a phone app — simple steps

You will do 4 things: put the code on GitHub, turn it into a live
website on Render, set up phone push notifications, and add it to
your home screen.

---

## Part 1 — Put the code on GitHub

1. Go to https://github.com and click **Sign up** (skip if you
   already have an account). It's free.
2. Once signed in, click the **+** in the top right → **New
   repository**.
3. Name it `stock-app`. Leave everything else as-is. Click
   **Create repository**.
4. On the next page, click **uploading an existing file**.
5. Unzip the `stock-app.zip` I gave you, then drag all the files
   inside it into that upload box.
6. Scroll down, click **Commit changes**.

Your code is now on GitHub.

---

## Part 2 — Make it a live website (Render)

1. Go to https://render.com and click **Get Started** → sign up
   using your GitHub account (easiest — one click).
2. Click **New +** → **Web Service**.
3. Choose **Build and deploy from a Git repository**, then pick the
   `stock-app` repository you just made.
4. Fill in:
   - **Name:** `stock-app` (or anything)
   - **Region:** closest to you
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free
5. Before clicking create, scroll to **Environment Variables** and
   add these one at a time (click **Add Environment Variable** for
   each):
   - `NTFY_TOPIC` → (see Part 3 below — come back and fill this in)
   - `CHECK_MINUTES` → `15`
6. Click **Create Web Service**.

Render will now build your app. This takes a few minutes. When it
says **Live** at the top, click the link it gives you (something like
`https://stock-app-xxxx.onrender.com`) — that's your app's website
address. Save it somewhere.

**Note:** the free plan sleeps after 15 minutes of no visits, and
wakes up again (takes ~30 seconds) next time you or the scheduler
visits it. That's normal for free hosting.

---

## Part 3 — Set up push notifications (ntfy)

1. On your phone, install the app called **ntfy** (search your app
   store), OR just use it in your phone's browser at https://ntfy.sh
   — either works.
2. Pick a secret topic name only you would guess — for example
   `sweed-stocks-8k2`. Write it down.
3. In the ntfy app, tap **+** and subscribe to that exact topic name.
4. Go back to Render (Part 2, step 5) and set `NTFY_TOPIC` to that
   same exact name. Click **Save Changes** — Render will restart
   your app automatically.

From now on, any alert your app finds will pop up on your phone as a
notification, even if the app isn't open.

---

## Part 4 — Add it to your home screen

1. Open your app's website address from Part 2 in your phone's
   browser (Safari on iPhone, Chrome on Android).
2. **iPhone:** tap the Share icon → **Add to Home Screen**.
   **Android:** tap the ⋮ menu → **Add to Home screen** (or
   **Install app**).
3. Give it a name like "Stock Alerts" and confirm.

You now have an icon on your home screen that opens your live stock
alert app, with push notifications working in the background.

---

## Editing your watchlist later

To change which stocks you watch or their thresholds, edit
`watchlist.json` right on GitHub (open the file, click the pencil
icon to edit, then **Commit changes**) — Render will automatically
rebuild and update your live app within a couple of minutes.
