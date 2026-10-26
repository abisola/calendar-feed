# Calendar feed – next two weeks

A daily job that reads a public Google Calendar, keeps only the next 14 days of events (with recurring events expanded into individual occurrences) and publishes them as `calendar.ics` at a public URL.

## How it works

1. GitHub Actions runs `fetch_calendar.py` once a day (and whenever you trigger it by hand).
2. The script downloads the calendar's public iCal feed – no Google API key needed.
3. It writes `public/calendar.ics`, which is deployed to GitHub Pages.
4. You download it from the GitHub Pages address shown when the workflow finishes, plus `/calendar.ics`.

If the fetch fails, the workflow fails and the previously published file stays live – you never get an empty calendar.

## Set-up (about 10 minutes)

### 1. Get the calendar address

In Google Calendar: **Settings → (your calendar) → Access permissions** – tick *Make available to public*. Then under **Integrate calendar**, copy either the **Calendar ID** or the **Public address in iCal format**. The script accepts both.

### 2. Create the repository

1. Create a new GitHub repository (for example `calendar-feed`).
2. Upload these files, keeping the folder structure:
   - `fetch_calendar.py`
   - `requirements.txt`
   - `.github/workflows/refresh-calendar.yml`
   - `README.md`

### 3. Add the calendar as a secret

**Settings → Secrets and variables → Actions → New repository secret**

- Name: `CALENDAR_ID`
- Value: the ID or iCal address from step 1

### 4. Turn on GitHub Pages

**Settings → Pages → Build and deployment → Source: GitHub Actions**

### 5. Run it once

**Actions → Refresh calendar feed → Run workflow**. When it finishes, the deploy step shows the site URL. Your file is at that URL plus `calendar.ics`.

## Using it on another computer

- **One-off download:** open the URL in a browser.
- **Stay in sync:** use your calendar app's "subscribe to a calendar by URL" option and paste the address. It will pick up the daily refresh automatically.
- **Scripted download:** `curl -o calendar.ics <your-pages-address>/calendar.ics`

## Options

| Setting | Where | Default |
|---|---|---|
| Days ahead | `DAYS_AHEAD` in the workflow | `14` |
| Run time | `cron` line in the workflow (UTC) | `17 5 * * *` – 05:17 UTC daily |

## Things to know

- **The published URL is public.** Anyone with the link can read it – fine for a calendar that is already public, but don't point this at a private calendar's secret address.
- **Inactivity pause.** GitHub disables scheduled workflows in a repository after 60 days with no activity. If that happens, a banner appears on the Actions tab – click *Enable workflow*. Pushing any small commit every couple of months avoids it.
- **Timing.** Scheduled runs can be delayed at busy times, so treat 05:17 as "early morning" rather than exact.

## Testing locally

```bash
pip install -r requirements.txt
CALENDAR_ID="your-calendar-id@group.calendar.google.com" python fetch_calendar.py
# or test against a file:
SOURCE_FILE=sample.ics OUTPUT_FILE=out.ics python fetch_calendar.py
```
