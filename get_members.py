import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import csv
import requests

# Load environment variables
load_dotenv()

# Get login credentials and Make webhook url from environment variables
USER = os.getenv("ISSA_USER")
PASS = os.getenv("ISSA_PASS")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# Check to ensure required environment variables are found
if not USER or not PASS or not MAKE_WEBHOOK_URL:
    raise ValueError("ISSA_USER or ISSA_PASS or MAKE_WEBHOOK_URL not found — check your .env file")

# Define directory for file downloads
DOWNLOAD_DIR = Path("downloads")
# If file does not exist create it
DOWNLOAD_DIR.mkdir(exist_ok=True)


def run():
    """
    Log into the ISSA member portal, navigate to the Kentuckiana group,
    trigger the member export, and save the resulting CSV locally.

    Returns:
        Path: Location of the downloaded CSV file (downloads/issa_members.csv).
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()

        # Navigate to ISSA login page
        page.goto("https://www.members.issa.org/Login.aspx")

        # Accept cookies
        accept_btn = page.get_by_role("button", name="Accept")
        try:
            accept_btn.wait_for(state="visible", timeout=5000)
            accept_btn.click()
        except Exception:
            pass  # popup didn't appear this run, that's fine

        # Fill credentials and sign in
        page.get_by_role("textbox", name="Username").fill(USER)
        page.get_by_role("textbox", name="Password").fill(PASS)
        page.get_by_role("button", name="Sign In").click()

        # Confirm login succeeded before continuing
        page.wait_for_selector("#navbar", timeout=15000)
        print("Login confirmed.")

        # Navigate to group
        page.locator("#navbar").get_by_role("link", name=" Groups").click()
        page.get_by_role("link", name="edit Manage Group").click()

        # Trigger export
        page.get_by_role("button", name=" Actions").click()
        page.get_by_role("button", name=" Admin").click()


        with page.expect_download() as download_info:
            with page.expect_popup() as popup_info:
                page.get_by_role("link", name=" Export Group Members").click()
            popup = popup_info.value
            popup.get_by_role("link", name="Click here to download.").click()

        download = download_info.value
        save_path = DOWNLOAD_DIR / "issa_members.csv"
        download.save_as(save_path)
        print(f"Downloaded to: {save_path}")

        popup.close()
        page.close()
        context.close()
        browser.close()

        return save_path

# Define required columns in CSV export
COLUMNS_TO_KEEP = ["Web_Site_Member_ID","Email_Address","First_Name","Last_Name","Organization","Professional_Title","Primary_Location","Date_Membership_Expires","Date_Joined"]

def clean_row(row: dict) -> dict:
    """
    Helper function to filter a CSV row down to only the fields Make needs.
    """
    return {k: row[k] for k in COLUMNS_TO_KEEP if k in row}


def send_to_make(csv_path: Path):
    """
    Parse a member export CSV and post each cleaned row to the Make webhook.
    
    Args:
        csv_path: Path to the exported CSV file to read and send.
    Returns:
        bool: True if every row was sent successfully, False if any failed.
    """
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [clean_row(row) for row in reader]

    print(f"Found {len(rows)} rows. Posting to Make...")

    all_succeeded = True
    for i, row in enumerate(rows, start=1):
        try:
            response = requests.post(MAKE_WEBHOOK_URL, json=row, timeout=10)
            if response.status_code != 200:
                print(f"Row {i} failed ({response.status_code}): {row}")
                all_succeeded = False
            else:
                print(f"Row {i} sent.")
        except requests.RequestException as e:
            print(f"Row {i} errored: {e}")
            all_succeeded = False

    return all_succeeded


if __name__ == "__main__":
    file_path = run()
    print("Export complete:", file_path)

    success = send_to_make(file_path)

    if success:
        file_path.unlink()
        print(f"Deleted local file: {file_path}")
    else:
        print(f"Some rows failed to send — keeping {file_path} for retry.")
