import json
import re
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import websocket

from scrape import load_data, parse_survey_page, save_data


DEBUG_PORT = 9222
BASE_URL = "https://www.thegradcafe.com"
OUTPUT_FILE = Path("applicant_data.json")
PROFILE_FOLDER = Path("chrome_capture_profile")

# Keep this small while validating the optimized workflow.
MAX_PAGES = 2

# Polite pause between normal public pages.
PAGE_DELAY_SECONDS = 4

# Save applicant_data.json every N newly captured pages.
# Each HTML page is still saved immediately, so if the program is interrupted
# before the next JSON checkpoint, scrape.py can rebuild the missing records.
SAVE_EVERY_PAGES = 25


CHROME_PATHS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
]


def _find_chrome():
    """Find the Chrome executable on Windows."""
    for path in CHROME_PATHS:
        if path.exists():
            return path

    raise FileNotFoundError(
        "Google Chrome could not be found in the expected locations."
    )


def _start_chrome():
    """Start a separate Chrome window with remote debugging enabled."""
    chrome_path = _find_chrome()
    profile_path = PROFILE_FOLDER.resolve()

    command = [
        str(chrome_path),
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={profile_path}",
        "--remote-allow-origins=http://127.0.0.1:9222",
        f"{BASE_URL}/survey/",
    ]

    subprocess.Popen(command)

    print("Starting a separate Chrome capture window...")
    time.sleep(3)


def _get_tabs():
    """Return the Chrome tabs exposed through the debugging port."""
    with urlopen(
        f"http://127.0.0.1:{DEBUG_PORT}/json",
        timeout=5,
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def _find_gradcafe_tab():
    """Find the open GradCafe survey tab."""
    tabs = _get_tabs()

    for tab in tabs:
        url = tab.get("url", "")

        if "thegradcafe.com/survey" in url:
            return tab

    return None


def _wait_for_gradcafe_tab(timeout=10, poll_interval=0.25):
    """Wait briefly for the GradCafe tab to reappear after navigation."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            tab = _find_gradcafe_tab()
            if tab is not None:
                return tab
        except Exception:
            pass

        time.sleep(poll_interval)

    return None


def _send_cdp(tab, method, params=None):
    """Send one Chrome DevTools Protocol command."""
    socket = websocket.create_connection(
        tab["webSocketDebuggerUrl"],
        origin=f"http://127.0.0.1:{DEBUG_PORT}",
        timeout=10,
    )

    try:
        message = {
            "id": 1,
            "method": method,
        }

        if params is not None:
            message["params"] = params

        socket.send(json.dumps(message))

        while True:
            response = json.loads(socket.recv())

            if response.get("id") == 1:
                return response

    finally:
        socket.close()


def _capture_html(tab, retries=6, retry_delay=0.5):
    """Capture rendered HTML, retrying briefly during page transitions."""
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = _send_cdp(
                tab,
                "Runtime.evaluate",
                {
                    "expression": "document.documentElement.outerHTML",
                    "returnByValue": True,
                },
            )

            value = (
                response.get("result", {})
                .get("result", {})
                .get("value")
            )

            if isinstance(value, str) and value:
                return value

            last_error = RuntimeError(
                "Chrome returned a temporary Runtime.evaluate response "
                "without HTML."
            )

        except Exception as exc:
            last_error = exc

        if attempt < retries:
            time.sleep(retry_delay)

    raise RuntimeError(
        f"Could not capture page HTML after {retries} attempts."
    ) from last_error


def _navigate(tab, url):
    """Navigate the existing Chrome tab to a normal public URL."""
    _send_cdp(
        tab,
        "Page.navigate",
        {
            "url": url,
        },
    )


def _get_result_urls(html):
    """Extract GradCafe result URLs from the rendered survey page."""
    result_ids = re.findall(r'/result/(\d+)', html)

    return {
        f"{BASE_URL}/result/{result_id}"
        for result_id in result_ids
    }


def _next_filename():
    """Choose the next survey_page_N.html filename."""
    existing = list(Path(".").glob("survey_page*.html"))
    highest_number = 0

    for path in existing:
        if path.name == "survey_page.html":
            highest_number = max(highest_number, 1)
            continue

        match = re.fullmatch(
            r"survey_page_(\d+)\.html",
            path.name,
        )

        if match:
            highest_number = max(
                highest_number,
                int(match.group(1)),
            )

    return Path(f"survey_page_{highest_number + 1}.html")


def _find_next_url(html):
    """
    Find the normal next-page survey URL.

    GradCafe uses cursor-based pagination.
    """
    links = re.findall(
        r'href=["\']([^"\']*survey\?cursor=[^"\']+)["\']',
        html,
        flags=re.IGNORECASE,
    )

    if not links:
        return None

    # This worked correctly in the 10-page test.
    next_url = links[-1]
    next_url = next_url.replace("&amp;", "&")

    if next_url.startswith("/"):
        next_url = BASE_URL + next_url

    elif next_url.startswith("survey"):
        next_url = f"{BASE_URL}/{next_url}"

    return next_url


def _looks_blocked(html):
    """
    Detect obvious verification/block pages.

    IMPORTANT:
    We stop. We do not attempt to solve or bypass them.
    """
    text = html.lower()

    blocked_phrases = [
        "verify you are human",
        "verification required",
        "checking your browser",
        "challenge-platform",
        "cf-chl",
        "access denied",
        "too many requests",
        "rate limit",
    ]

    return any(
        phrase in text
        for phrase in blocked_phrases
    )


def _wait_for_results(tab, timeout=30):
    """Wait until an ordinary survey results page is visible."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        html = _capture_html(tab)
        result_urls = _get_result_urls(html)

        # Real applicant links take priority over harmless Cloudflare strings
        # that may remain in an otherwise normal page.
        if result_urls:
            return html

        if _looks_blocked(html):
            return html

        time.sleep(1)

    return _capture_html(tab)


def _append_page_records(html, data, existing_urls):
    """
    Parse only the newly captured page and append unseen records in memory.

    This avoids rerunning scrape.py and reparsing every older HTML page after
    every capture.
    """
    page_records = parse_survey_page(html)

    added = 0

    for record in page_records:
        url = record.get("url", "")

        if url and url not in existing_urls:
            data.append(record)
            existing_urls.add(url)
            added += 1

    return len(page_records), added


def capture_pages(web_mode=False):
    """
    Capture a batch of ordinary public GradCafe pages.

    Cloudflare verification remains manual.
    The program stops rather than bypassing verification/blocking.
    """

    try:
        tab = _find_gradcafe_tab()
    except Exception:
        tab = None

    if web_mode:
        if tab is None:
            raise RuntimeError(
                "Open your GradCafe Chrome capture window, complete any "
                "verification manually, and navigate to a survey page "
                "showing applicant results. Then click Pull Data again."
            )

        html = _wait_for_results(tab, timeout=10)
        if not _get_result_urls(html):
            raise RuntimeError(
                "GradCafe applicant results are not visible in Chrome. "
                "Complete any verification manually, wait for the "
                "results to appear, and click Pull Data again."
            )

        print("GradCafe results are visible. Starting web capture.")

    else:
        if tab is None:
            print("A compatible Chrome window was not found.")
            _start_chrome()

            print()
            print("Chrome started.")
            print()
            print("In the Chrome window:")
            print("1. Complete any Cloudflare verification manually.")
            print("2. Go to the GradCafe survey page where you want to resume.")
            print("3. Make sure applicant results are visible.")
            print("4. Return here and press Enter.")
            print()

            input(
                "After the GradCafe page is fully loaded, "
                "press Enter here..."
            )

            tab = _find_gradcafe_tab()

            if tab is None:
                print("Could not find the GradCafe survey tab.")
                return

        else:
            print("Found the existing GradCafe Chrome window.")
            print()
            print(
                "Make sure the Chrome window is on the "
                "survey page where you want to resume."
            )

            input(
                "When the results are visible, "
                "press Enter here..."
            )

    # Load the accumulated JSON only once for this whole run.
    data = load_data()
    existing_urls = {
        record.get("url")
        for record in data
        if record.get("url")
    }

    print()
    print(f"Currently saved records: {len(existing_urls)}")
    print(f"Automatic test limit: {MAX_PAGES} pages")
    print()

    captured_count = 0
    unsaved_pages = 0

    try:
        for batch_number in range(1, MAX_PAGES + 1):

            # Refresh tab metadata because its URL changes as we paginate.
            # Chrome can briefly omit the tab from the debugging endpoint during
            # navigation, so retry for a few seconds instead of stopping immediately.
            tab = _wait_for_gradcafe_tab()

            if tab is None:
                print("The GradCafe tab could not be found after retrying. Stopping.")
                break

            print("=" * 60)
            print(f"Batch page {batch_number} of {MAX_PAGES}")
            print(f"Current URL: {tab.get('url', '')}")

            html = _wait_for_results(tab)
            result_urls = _get_result_urls(html)

            # NEVER continue through a challenge page.
            if not result_urls and _looks_blocked(html):
                print()
                print(
                    "GradCafe appears to be requesting verification "
                    "or blocking the request."
                )
                print("Stopping automatically.")
                break

            print(f"Found {len(result_urls)} result links.")

            if not result_urls:
                print("No applicant results were found. Stopping.")
                break

            new_urls = result_urls - existing_urls

            print(f"New results on page: {len(new_urls)}")
            print(
                "Already saved from this page: "
                f"{len(result_urls - new_urls)}"
            )

            if new_urls:
                # Save the raw rendered page immediately for traceability
                # and recovery if the program is interrupted.
                filename = _next_filename()
                filename.write_text(
                    html,
                    encoding="utf-8",
                )

                print(f"Saved as {filename.name}")

                parsed_count, added_count = _append_page_records(
                    html,
                    data,
                    existing_urls,
                )

                print(
                    f"Parsed {parsed_count} applicant records "
                    f"from {filename.name}."
                )
                print(
                    f"Added {added_count} new records in memory."
                )

                captured_count += 1
                unsaved_pages += 1

                # Checkpoint the JSON periodically instead of rewriting the
                # growing file after every single page.
                if unsaved_pages >= SAVE_EVERY_PAGES:
                    save_data(data)
                    unsaved_pages = 0
                    print(
                        f"Checkpoint saved: {len(data)} total records "
                        f"in applicant_data.json."
                    )

            else:
                print(
                    "This page is already present in "
                    "applicant_data.json."
                )

            next_url = _find_next_url(html)

            if not next_url:
                print()
                print("Could not locate the normal next-page URL.")
                print("Stopping.")
                break

            print()
            print(
                f"Waiting {PAGE_DELAY_SECONDS} seconds "
                "before the next page..."
            )

            time.sleep(PAGE_DELAY_SECONDS)

            print(f"Navigating to: {next_url}")
            _navigate(tab, next_url)


    finally:
        # Always save any records accumulated since the previous checkpoint,
        # including when the run stops because of an error or verification.
        if unsaved_pages > 0:
            save_data(data)
            print()
            print(
                f"Final checkpoint saved: {len(data)} total records "
                f"in applicant_data.json."
            )

    print()
    print("=" * 60)
    print("Capture run finished.")
    print(f"New HTML pages captured: {captured_count}")
    print(f"Records currently in applicant_data.json: {len(data)}")


if __name__ == "__main__":
    capture_pages()
