# ISSA Member Retriever

Automates exporting ISSA Kentuckiana chapter membership data from the ISSA international member portal and syncing it to a [Make](https://www.make.com) scenario via webhook.

## What it does

1. Logs into the ISSA member portal (`members.issa.org`) using Playwright
2. Navigates to the Kentuckiana chapter group and triggers a member export
3. Downloads the resulting CSV
4. Parses the CSV, keeping only the fields needed downstream
5. Posts each member record to a Make webhook
6. Deletes the local CSV once every record has been sent successfully

## Requirements

- Python 3.10+
- A `.env` file with valid credentials (see below)
- An active Make scenario with a webhook trigger

## Setup

**1. Clone the repo and enter the project folder**

```bash
git clone <repo-url>
cd issa_member_retriever
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
playwright install
```

**4. Configure environment variables**

Copy the example file and fill in real values:

```bash
cp .env.example .env
```

`.env` requires:

```
ISSA_USER=your_issa_username
ISSA_PASS=your_issa_password
MAKE_WEBHOOK_URL=https://hook.us1.make.com/your_webhook_id
```

`.env` is git-ignored and should never be committed.

## Usage

Run the script from an activated virtual environment:

```bash
python issa_member_retriever.py
```

The script will:
- Open a visible Chromium browser window (headless is currently disabled for
  easier debugging)
- Log in and download the current member export to `downloads/issa_members.csv`
- Post each row to the Make webhook
- Delete the local CSV if every row sent successfully; otherwise it's kept
  for troubleshooting/retry

## Project structure

```
issa_member_retriever/
├── issa_member_retriever.py   # Main script
├── requirements.txt           # Python dependencies
├── .env.example               # Template for required environment variables
├── .gitignore
└── downloads/                 # Local CSV export (git-ignored, created at runtime)
```

## Configuration notes

- **Columns sent to Make** are controlled by `COLUMNS_TO_KEEP` near the top
  of the script. Update this list if the ISSA export format changes or if
  different fields are needed downstream.
- **Make Data Store key**: when mapping fields in Make, use
  `Web_Site_Member_ID` as the unique key on the Data Store's "Add/Replace a
  Record" module so re-running the export updates existing members instead
  of creating duplicates.
- This script currently sends **one webhook request per member row**. For
  large membership lists, be mindful of Make's operation limits on your plan.

## Known limitations / future improvements

- No handling yet for members who drop off the export (removed/lapsed
  members currently remain in the Make Data Store unless removed manually).
- Runs headed (`headless=False`) by default — useful for debugging, but
  would need to be switched to headless for unattended/scheduled runs.
- No automatic retry logic if individual webhook rows fail; failed rows are
  logged to the console only.

## Security

- Never commit `.env` — it's excluded via `.gitignore`.
- If credentials are ever accidentally exposed (e.g., committed, pasted
  somewhere, shared in a chat), rotate the ISSA password and regenerate the
  Make webhook URL immediately.
