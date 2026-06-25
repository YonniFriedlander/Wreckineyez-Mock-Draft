WRECKINEYEZ MOCK DRAFT — HOSTED VERSION
==========================================

This version is for hosting on GitHub Pages so your league mates just
visit a URL — no downloads, no Python, no macOS Gatekeeper warnings.


WHAT'S DIFFERENT FROM THE DOWNLOAD VERSION
--------------------------------------------
Instead of running a local proxy that fetches FantasyPros live, this
version reads two small JSON files (rankings.json, rankings-adp.json)
that sit next to index.html. You update those files yourself whenever
you want fresh rankings — takes about 30 seconds, no coding.


ONE-TIME SETUP — GITHUB PAGES (about 5 minutes)
---------------------------------------------------

STEP 1 — Create a GitHub account (skip if you already have one)
  Go to https://github.com/signup and follow the prompts. Free.

STEP 2 — Create a new repository
  a. Click the "+" icon in the top-right corner of any GitHub page,
     then click "New repository"
  b. Repository name: anything you like, e.g. "wreckineyez-draft"
  c. Set visibility to "Public" — this is REQUIRED for GitHub Pages
     to work on a free account (private repos need a paid plan)
  d. Leave everything else as default
  e. Click "Create repository"

STEP 3 — Upload the files
  a. On your new (empty) repository page, click
     "uploading an existing file" (or "Add file" → "Upload files")
  b. Drag in all 6 files from this folder:
       index.html
       rankings.json
       rankings-adp.json
       generate_rankings_json.py
       fp_proxy.py
       README.txt
  c. Scroll down, click "Commit changes"

STEP 4 — Turn on GitHub Pages
  a. On your repository page, click "Settings" (top menu bar)
  b. In the left sidebar, under "Code and automation", click "Pages"
  c. Under "Build and deployment" → "Source", select "Deploy from
     a branch"
  d. Under "Branch", select "main" and folder "/ (root)", then
     click "Save"
  e. Wait 1-2 minutes. Refresh the Pages settings page — it will
     show "Your site is live at https://yourusername.github.io/
     wreckineyez-draft/" with a link

STEP 5 — Share the link
  Copy that URL and send it to your league. They just open it in a
  browser like any website — nothing to download or install.


UPDATING RANKINGS (whenever you want fresh data)
---------------------------------------------------
1. Make sure fp_proxy.py is in this same folder on your computer
   (it should already be there from this zip).

2. Open a terminal in this folder and run:

     python3 generate_rankings_json.py

   This fetches BOTH ECR and ADP rankings in one run and writes
   rankings.json and rankings-adp.json right here, overwriting the
   old ones.

3. Upload BOTH updated .json files together, in a single commit:
     a. Go to your repository on GitHub
     b. Click "Add file" → "Upload files"
     c. Drag in BOTH rankings.json and rankings-adp.json at the
        same time (select/drag them together, not one after another)
     d. Click "Commit changes" once — this replaces the old versions
        with your new ones in a single update

4. Wait about a minute for GitHub Pages to rebuild. Anyone who opens
   (or refreshes) the site afterward gets the new rankings
   automatically — no action needed on their end.


WHAT'S IN THIS FOLDER
------------------------
index.html                   The draft app (rename of MockDraft.html)
rankings.json                Static ECR rankings the app loads on open
rankings-adp.json            Static ADP rankings (used by "Reload" → ADP)
generate_rankings_json.py    Run this to refresh the two JSON files
fp_proxy.py                  Used internally by generate_rankings_json.py
                              (the same fetching engine from the proxy)


TROUBLESHOOTING
------------------
"My site shows a 404" — Double check Settings → Pages shows a green
  "Your site is live" message. It can take a few minutes after first
  enabling Pages. Also confirm the branch/folder match what you
  uploaded to (main / root).

"My rankings didn't update" — Make sure you uploaded BOTH json files
  in the same commit, and check the repository's main page to confirm
  the file timestamps changed. GitHub Pages can take 1-2 minutes to
  rebuild after a commit.

"Friends see an empty player list" — This means rankings.json is
  still the empty placeholder. Run generate_rankings_json.py and
  upload the result (see "Updating rankings" above).


NOTES
------
- This repo will be PUBLIC, meaning anyone with the link (or anyone
  searching GitHub) can view the files. There's nothing sensitive in
  here — no passwords or API keys — but keep that in mind.
- If FantasyPros changes their page layout and generate_rankings_json.py
  stops working, league mates can still load a CSV manually from the
  Rankings tab in the app — that fallback always works.
- Each person's draft progress, notes, and keeper settings are saved
  in their own browser's local storage — nothing is shared between
  users, and nothing is sent to any server. This is purely a static
  site; there's no backend to maintain or pay for.
- GitHub Pages free tier: ~100GB bandwidth/month (soft limit), no
  cap on commits/updates. For a league this size, you will not come
  close to hitting any limit.
