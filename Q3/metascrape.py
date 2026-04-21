import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

COUNTRIES = ["US", "GB", "DE", "FR", "AU"]
SEARCH_TERMS = {
    "pro_immigration": [
        "welcome refugees", "immigration reform", "path to citizenship",
        "dreamers", "open borders", "immigrant rights"
    ],
    "anti_immigration": [
        "secure the border", "illegal immigration", "deportation",
        "border wall", "immigration enforcement", "stop illegal"
    ]
}

def human_delay(min=1.5, max=4.0):
    time.sleep(random.uniform(min, max))

def scroll_page(page, scrolls=5):
    for _ in range(scrolls):
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
        human_delay(1, 2.5)

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
            headless=False,  # keep visible to avoid detection
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        # Remove webdriver fingerprint
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page.goto(url, wait_until="domcontentloaded")
        human_delay(3, 5)

        # Dismiss cookie/login prompts if they appear
        try:
            page.click('[aria-label="Close"]', timeout=3000)
        except:
            pass

        # Scroll to load more ads
        scroll_page(page, scrolls=8)

        # Parse the loaded content
        soup = BeautifulSoup(page.content(), "html.parser")
        ad_cards = soup.find_all("div", {"class": lambda c: c and "xh8yej3" in c})

        for card in ad_cards:
            ad_data = {
                "country": country,
                "search_term": search_term,
                "label": label,  # pro_immigration or anti_immigration
                "page_name": extract_page_name(card),
                "ad_text": extract_ad_text(card),
                "start_date": extract_date(card),
                "spend_estimate": extract_spend(card),
                "impressions": extract_impressions(card),
            }
            ads.append(ad_data)

        browser.close()

    return ads


def extract_page_name(card):
    try:
        return card.find("a", {"role": "link"}).get_text(strip=True)
    except:
        return None

def extract_ad_text(card):
    try:
        # Ad body text is usually in a span inside the card
        spans = card.find_all("span")
        texts = [s.get_text(strip=True) for s in spans if len(s.get_text(strip=True)) > 30]
        return " | ".join(texts[:3])  # take first few substantial text blocks
    except:
        return None

def extract_date(card):
    try:
        date_div = card.find("div", string=lambda t: t and "Started running" in t)
        return date_div.get_text(strip=True) if date_div else None
    except:
        return None

def extract_spend(card):
    try:
        spend_div = card.find("div", string=lambda t: t and "$" in str(t))
        return spend_div.get_text(strip=True) if spend_div else None
    except:
        return None

def extract_impressions(card):
    try:
        imp_div = card.find("div", string=lambda t: t and "impression" in str(t).lower())
        return imp_div.get_text(strip=True) if imp_div else None
    except:
        return None


def run_scrape(countries=COUNTRIES, terms=SEARCH_TERMS):
    all_ads = []

    for country in countries:
        for label, term_list in terms.items():
            for term in term_list:
                print(f"Scraping: [{country}] [{label}] '{term}'")
                try:
                    ads = scrape_ad_library(country, term, label)
                    all_ads.extend(ads)
                    print(f"  → {len(ads)} ads found")
                except Exception as e:
                    print(f"  → Failed: {e}")

                # Longer delay between searches to avoid rate limiting
                human_delay(5, 12)

    df = pd.DataFrame(all_ads)
    df.to_csv("immigration_ads.csv", index=False)
    print(f"\nDone. {len(all_ads)} total ads saved.")
    return df

df = run_scrape()

from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

def classify_ad(text):
    if not text:
        return None
    result = classifier(text, ["pro-immigration", "anti-immigration", "neutral"])
    return result["labels"][0]

df["nlp_label"] = df["ad_text"].apply(classify_ad)