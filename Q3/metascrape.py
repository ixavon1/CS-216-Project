import time
import random
import re
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

COUNTRIES = ["AT", "BE", "CO", "DE", "HU", "IT", "ES", "SE", "US"]

SEARCH_TERMS = {
    "pro_immigration": [
        "welcome refugees", "immigration reform", "path to citizenship",
        "dreamers", "open borders", "immigrant rights", "refugee resettlement",
        "we are all immigrants"
    ],
    "anti_immigration": [
        "secure the border", "illegal immigration", "deportation",
        "border wall", "immigration enforcement", "stop illegal",
        "mass deportation", "build the wall"
    ]
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def human_delay(min=1.5, max=4.0):
    time.sleep(random.uniform(min, max))

def scroll_page(page, scrolls=5):
    for _ in range(scrolls):
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        human_delay(1, 2.5)

def extract_page_name(card):
    try:
        return card.find("a", {"role": "link"}).get_text(strip=True)
    except:
        return None

def extract_spend(card):
    try:
        text = card.get_text(" ", strip=True)
        match = re.search(
            r'Amount spent[^:]*:\s*([A-Z$€£₹]*[\$€£]?[\d,\.]+[KM]?\s*[-–]\s*[A-Z$€£₹]*[\$€£]?[\d,\.]+[KM]?)',
            text
        )
        if match:
            return match.group(1).strip()
    except:
        pass
    return None

def estimate_midpoint(spend_range: str):
    """Convert a spend range like '$1,000 - $1,999' to its midpoint 1499.5."""
    if not spend_range or pd.isna(spend_range):
        return None
    parts = re.split(r'\s*[-–]\s*', spend_range.strip())
    if len(parts) != 2:
        return None
    def to_float(s):
        s = re.sub(r'[A-Z]?\$|€|£|₹|\s', '', s.strip())
        multiplier = 1
        if s and s[-1].upper() in {"K": 1_000, "M": 1_000_000}:
            multiplier = {"K": 1_000, "M": 1_000_000}[s[-1].upper()]
            s = s[:-1]
        try:
            return float(s.replace(",", "")) * multiplier
        except:
            return None
    low, high = to_float(parts[0]), to_float(parts[1])
    if low is None or high is None:
        return None
    return (low + high) / 2

# ─────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────

def scrape_ad_library(country: str, search_term: str, label: str):
    ads = []
    url = (
        f"https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=political_and_issue_ads"
        f"&country={country}&q={search_term.replace(' ', '+')}"
        f"&media_type=all"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            human_delay(3, 5)

            # Dismiss prompts
            try:
                page.click('[aria-label="Close"]', timeout=3000)
            except:
                pass

            scroll_page(page, scrolls=5)

            soup = BeautifulSoup(page.content(), "html.parser")

            # Select cards by content rather than fragile class names
            all_divs = soup.find_all("div")
            ad_cards = [
                d for d in all_divs
                if d.find(string=re.compile(r'Paid for by|Amount spent|Started running', re.I))
                and len(d.get_text(strip=True)) > 80
            ]

            # Deduplicate cards by text fingerprint before parsing
            seen = set()
            unique_cards = []
            for card in ad_cards:
                fingerprint = card.get_text(strip=True)[:120]
                if fingerprint not in seen:
                    seen.add(fingerprint)
                    unique_cards.append(card)

            for card in unique_cards:
                page_name   = extract_page_name(card)
                spend_range = extract_spend(card)

                # Skip cards with nothing useful
                if not page_name and not spend_range:
                    continue

                ads.append({
                    "country":       country,
                    "search_term":   search_term,
                    "label":         label,
                    "page_name":     page_name,
                    "spend_range":   spend_range,
                    "spend_midpoint": estimate_midpoint(spend_range),
                })

        except Exception as e:
            print(f"  ✗ Error [{country}] '{search_term}': {e}")
        finally:
            browser.close()

    return ads

# ─────────────────────────────────────────────
# MAIN RUN
# ─────────────────────────────────────────────

def run_scrape(countries=COUNTRIES, terms=SEARCH_TERMS, output_file="immigration_ads.csv"):
    all_ads = []

    for country in countries:
        for label, term_list in terms.items():
            for term in term_list:
                print(f"→ [{country}] [{label}] '{term}'")
                try:
                    ads = scrape_ad_library(country, term, label)
                    all_ads.extend(ads)
                    print(f"  ✓ {len(ads)} ads found")
                except Exception as e:
                    print(f"  ✗ Failed: {e}")
                human_delay(5, 12)

        # Save after each country so a crash doesn't lose everything
        pd.DataFrame(all_ads).to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"  ✓ Progress saved after {country}")

    df = pd.DataFrame(all_ads)

    # Dataframe-level deduplication
    df["raw_capture_count"] = df.groupby(
        ["country", "label", "page_name"]
    )["page_name"].transform("count")
    df.drop_duplicates(subset=["country", "label", "page_name", "spend_range"], inplace=True)
    df.dropna(subset=["page_name", "spend_range"], how="all", inplace=True)

    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n✓ Done. {len(df)} ads saved to '{output_file}'")

    # Summary
    print("\n── Ad counts per country and stance ────────────────")
    print(df.groupby(["country", "label"]).size().unstack(fill_value=0).to_string())
    print("\n── Total estimated spend per country and stance ────")
    print(df.groupby(["country", "label"])["spend_midpoint"].sum().unstack(fill_value=0).round(2).to_string())

    return df


if __name__ == "__main__":
    df = run_scrape()