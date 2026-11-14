# Putting the project online

Two steps: put the code on GitHub, then point Streamlit Community Cloud at it. Both are free.
At the end you have a public link for your CV. Allow about 20 minutes.

## Part 1: Put the code on GitHub

**1. Create a GitHub account** (skip if you have one)
Go to https://github.com/signup and follow the steps. Pick a professional username: it appears
in the link employers will see.

**2. Create an empty repository**
1. Go to https://github.com/new
2. In **Repository name** type: `arb-engine`
3. In **Description** type: `Physical crude arbitrage and voyage engine`
4. Select **Public**.
5. Leave "Add a README", ".gitignore" and "license" **unticked** (the project already has them).
6. Click **Create repository**.
7. Leave the page open. You will need the address it shows, which looks like
   `https://github.com/YOUR-USERNAME/arb-engine.git`

**3. Tell git who you are** (once only)
The commits so far carry a placeholder author name. Open a terminal in the project folder and
type these two lines, with your own name and the email on your GitHub account:

```
git config user.name "Your Name"
git config user.email "you@example.com"
```

If you would rather not show your email publicly, GitHub gives you a private one: go to
https://github.com/settings/emails, tick **Keep my email addresses private**, and use the
`...@users.noreply.github.com` address shown there instead.

Ask Claude to "rewrite the commit author to my name" if you want the earlier commits to show
your name too.

**4. Send the code to GitHub**
In the same terminal, type these three lines, replacing YOUR-USERNAME:

```
git remote add origin https://github.com/YOUR-USERNAME/arb-engine.git
git branch -M main
git push -u origin main
```

A browser window opens asking you to sign in to GitHub. Sign in and click **Authorize**.
When the terminal finishes, refresh the GitHub page: your files and the README with screenshots
should be there.

**Check:** the `.env` file and the `.venv` folder must NOT appear on GitHub. They are excluded
by `.gitignore`. (This project needs no API keys, so there is no `.env` at present.)

## Part 2: Deploy on Streamlit Community Cloud

**1. Sign in**
Go to https://share.streamlit.io and click **Continue with GitHub**. Authorize Streamlit when asked.

**2. Create the app**
1. Click **Create app** (top right), then **Deploy a public app from GitHub**.
2. **Repository:** choose `YOUR-USERNAME/arb-engine`
3. **Branch:** `main`
4. **Main file path:** type `app/main.py`
5. **App URL:** choose something short, for example `crude-arb-engine`
6. Click **Advanced settings**, set **Python version** to `3.12`, click **Save**.
7. Click **Deploy**.

The first build takes three to five minutes while it installs the packages. When it finishes, the
dashboard opens at `https://crude-arb-engine.streamlit.app` (or the name you chose).

**3. Check it**
- The "Start here" page shows today's ARB OPEN / ARB CLOSED verdict.
- The Prices page says "Freshly downloaded from EIA / World Bank". If it says it is showing the
  shipped snapshot instead, the download was blocked; click **Download the latest prices** to retry.
- Click through all six pages.

**4. Put the link on your CV**
Add the app link and the GitHub link, for example:

> Physical Crude Arbitrage & Voyage Engine: live dashboard (crude-arb-engine.streamlit.app),
> code (github.com/YOUR-USERNAME/arb-engine)

Also paste the app link into the **About** box on your GitHub repository page (the cog icon,
then **Website**).

## Keeping it up to date

- Free apps go to sleep after a few days without visitors. Anyone opening the link sees a "wake
  up" button and waits about a minute. Open it yourself the morning of an interview.
- When the code changes, type `git add -A`, `git commit -m "describe the change"`, `git push`.
  Streamlit redeploys automatically within a minute or two.
- The hire rates, canal surcharge, interest rate and bunker ratio are snapshots with a "checked"
  date. Before an interview, review the Methodology page and refresh anything stale in
  `data/assumptions/`.
