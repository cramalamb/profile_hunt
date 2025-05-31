# scraper.py

import os
import time
import csv
import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from login import get_driver, linkedin_login

# ────────────────────────────────────────────────────────────────────────────────
# 1) List of keywords to cross-reference against one company
KEYWORDS = [
    "university of chicago booth",
    "coast guard academy",
    "mckinsey",
    "u.s. coast guard",
    "navy",
    "army",
    "marines",
    "air force",
    "breakline"
]
# ────────────────────────────────────────────────────────────────────────────────


def scroll_page(driver):
    """
    Scroll to the bottom so LinkedIn lazy-loads any additional results.
    """
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)


def parse_contact_cards(driver):
    """
    Finds every <a> that has an href containing '/in/' and a nested <span aria-hidden="true">
    (the person's name). From there it climbs to the nearest ancestor <div> with
    'data-chameleon-result-urn' and extracts:

      - name       (from span[@aria-hidden='true'])
      - headline   (div with class 'fPKHunLoPKXcFGoTXEqoYXAPnXixUiYhgek')
      - location   (div with class 'WkjuHgoDAETDiNPzrVDpDLnexwXRWPettk')
      - profile_url (href of that <a>)

    Returns a list of dicts: [{"name","headline","location","profile_url"}, …].
    """
    cards_data = []

    # 1) Locate every <a> with '/in/' and a nested <span aria-hidden="true">
    name_links = driver.find_elements(
        By.XPATH,
        "//a[contains(@href,'/in/') and .//span[@aria-hidden='true']]"
    )

    for link in name_links:
        try:
            raw_url = link.get_attribute("href").split("?", 1)[0]
            name = link.find_element(By.XPATH, ".//span[@aria-hidden='true']").text.strip()
        except NoSuchElementException:
            continue

        # 2) Climb up to the container <div> that has 'data-chameleon-result-urn'
        try:
            container = link.find_element(
                By.XPATH,
                "./ancestor::div[@data-chameleon-result-urn]"
            )
        except NoSuchElementException:
            continue

        # 3) Extract headline
        try:
            headline_el = container.find_element(
                By.CSS_SELECTOR,
                "div.fPKHunLoPKXcFGoTXEqoYXAPnXixUiYhgek"
            )
            headline = headline_el.text.strip()
        except NoSuchElementException:
            headline = ""

        # 4) Extract location
        try:
            location_el = container.find_element(
                By.CSS_SELECTOR,
                "div.WkjuHgoDAETDiNPzrVDpDLnexwXRWPettk"
            )
            location = location_el.text.strip()
        except NoSuchElementException:
            location = ""

        cards_data.append({
            "name": name,
            "headline": headline,
            "location": location,
            "profile_url": raw_url
        })

    return cards_data


def prompt_int(prompt, default, min_v, max_v):
    """
    Ask the user for an integer between min_v and max_v (inclusive).
    If they press Enter, return default.
    """
    resp = input(f"{prompt} [default {default}, {min_v}-{max_v}]: ").strip()
    if resp.isdigit():
        val = int(resp)
        return max(min_v, min(val, max_v))
    return default


def main():
    # ─── Step 1: PROMPTS ─────────────────────────────────────────────────────────
    print("\n→ LINKEDIN SCRAPER: cross-reference single COMPANY vs. multiple KEYWORDS.\n")

    company = input("Enter the COMPANY to search for (e.g. 'breakline'): ").strip()
    while not company:
        print("   → Company cannot be blank.")
        company = input("Enter the COMPANY to search for (e.g. 'breakline'): ").strip()

    num_pages = prompt_int("How many pages per keyword to scrape", default=3, min_v=1, max_v=10)
    print(f"\n→ You chose to search {num_pages} page(s) per keyword.\n")

    # ─── Step 2: PREP OUTPUT ──────────────────────────────────────────────────────
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = "output"
    os.makedirs(out_dir, exist_ok=True)
    out_filename = f"{company.replace(' ', '_')}_{timestamp}.csv"
    out_path = os.path.join(out_dir, out_filename)

    # Instead of a set, use a dict keyed by URL: { profile_url: { "name":…, "headline":…, "location":…, "keywords": set(...) } }
    profiles = {}

    # ─── Step 3: LAUNCH SELENIUM & LOGIN ──────────────────────────────────────────
    driver = get_driver(headless=False)
    linkedin_login(driver)

    # ─── Step 4: LOOP OVER KEYWORDS ──────────────────────────────────────────────
    for kw in KEYWORDS:
        combined_query = f"{company} {kw}".strip().replace(" ", "%20")
        print(f"--- Searching for: '{company}' AND '{kw}' ---")

        search_url = (
            "https://www.linkedin.com/search/results/people/"
            f"?keywords={combined_query}&origin=GLOBAL_SEARCH_HEADER"
        )
        driver.get(search_url)
        time.sleep(2)

        for page in range(1, num_pages + 1):
            print(f"  • Page {page} for keyword '{kw}' …", end="", flush=True)
            scroll_page(driver)

            snippet_cards = parse_contact_cards(driver)
            print(f" found {len(snippet_cards)} cards.", flush=True)

            for card in snippet_cards:
                url = card["profile_url"]
                if url not in profiles:
                    # First time seeing this profile_url: initialize an entry
                    profiles[url] = {
                        "name": card["name"],
                        "headline": card["headline"],
                        "location": card["location"],
                        "keywords": set([kw])
                    }
                else:
                    # Already exists: just add this keyword to the set
                    profiles[url]["keywords"].add(kw)

            # Try to click “Next”
            try:
                nxt = driver.find_element(By.XPATH, "//button[@aria-label='Next']")
                nxt.click()
                time.sleep(2)
            except:
                print("    → No Next button (or last page).")
                break

    # ─── Step 5: WRITE TO CSV ───────────────────────────────────────────────────────
    if not profiles:
        print("\n[!] No profiles were collected. Check LinkedIn markup or login status.")
    else:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["name", "headline", "location", "profile_url", "matched_keywords"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for url, data in profiles.items():
                writer.writerow({
                    "name": data["name"],
                    "headline": data["headline"],
                    "location": data["location"],
                    "profile_url": url,
                    # Join all keywords (sorted) with a comma and space
                    "matched_keywords": ", ".join(sorted(data["keywords"]))
                })

        print(f"\n[✔] Scraped {len(profiles)} unique profiles across all keywords.")
        print(f"    Results saved to: {out_path}")

    driver.quit()


if __name__ == "__main__":
    main()
