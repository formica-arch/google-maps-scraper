from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import csv
import re
import time
import psutil
import os

from src.config import load_input


# ==========================================================
# LOGGER
# ==========================================================

def log(message=""):
    now = time.strftime("%H:%M:%S")
    print(f"[INFO] [{now}] {message}")


def warn(message=""):
    now = time.strftime("%H:%M:%S")
    print(f"[WARNING] [{now}] {message}")


def error(message=""):
    now = time.strftime("%H:%M:%S")
    print(f"[ERROR] [{now}] {message}")


# ==========================================================
# RUNTIME
# ==========================================================

START_TIME = time.time()

PROCESS = psutil.Process(os.getpid())


# ==========================================================
# REGEX
# ==========================================================

PLACE_ID_REGEX = re.compile(r'0x[0-9a-fA-F]+:0x[0-9a-fA-F]+')
LAT_REGEX_1 = re.compile(r'!3d(-?\d+\.\d+)')
LNG_REGEX_1 = re.compile(r'!4d(-?\d+\.\d+)')
LAT_REGEX_2 = re.compile(r'@(-?\d+\.\d+),')
LNG_REGEX_2 = re.compile(r'@-?\d+\.\d+,(-?\d+\.\d+)')


# ==========================================================
# HELPERS
# ==========================================================

def clean_text(text):

    if text is None:
        return ""

    text = str(text)

    replacements = [
        "\n",
        "\t",
        "\r",
        "\u202f",
        "",
        ""
    ]

    for item in replacements:
        text = text.replace(item, " ")

    text = " ".join(text.split())

    return text.strip()


def safe_text(locator):

    try:
        return clean_text(locator.inner_text(timeout=3000))
    except Exception:
        return ""


def safe_attribute(locator, attribute):

    try:
        value = locator.get_attribute(attribute, timeout=3000)
        return clean_text(value)
    except Exception:
        return ""


# ==========================================================
# MEMORY / CPU
# ==========================================================

def get_memory_usage():

    try:
        return round(PROCESS.memory_info().rss / 1024 / 1024, 2)
    except Exception:
        return 0


def get_cpu_usage():

    try:
        return round(psutil.cpu_percent(interval=0.1), 2)
    except Exception:
        return 0


# ==========================================================
# WAIT HELPERS
# ==========================================================

def wait_for_page(page, timeout=20000):

    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
        return
    except Exception:
        pass

    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except Exception:
        page.wait_for_timeout(1000)


def wait_after_open(page, delay_ms=1200):
    page.wait_for_timeout(delay_ms)


# ==========================================================
# SEARCH QUERY
# ==========================================================

def build_search_query(config):

    custom = (
        config.get("customSearchQuery")
        or config.get("searchQuery")
    )

    if custom:
        return custom

    searches = config.get("searchStringsArray", ["restaurant"])

    if not searches:
        searches = ["restaurant"]

    keyword = searches[0].strip()

    location = config.get("locationQuery", "").strip()

    if keyword and location:
        return f"{keyword} in {location}"

    if location:
        return location

    return keyword


# ==========================================================
# URL HELPERS
# ==========================================================

def extract_place_id(url):

    if not url:
        return ""

    match = PLACE_ID_REGEX.search(url)

    if match:
        return match.group(0)

    match = re.search(r'/place/([^/]+)', url)

    if match:
        return match.group(1)

    return ""


def extract_latitude(url):

    if not url:
        return ""

    match = LAT_REGEX_1.search(url)

    if match:
        return match.group(1)

    match = LAT_REGEX_2.search(url)

    if match:
        return match.group(1)

    return ""


def extract_longitude(url):

    if not url:
        return ""

    match = LNG_REGEX_1.search(url)

    if match:
        return match.group(1)

    match = LNG_REGEX_2.search(url)

    if match:
        return match.group(1)

    return ""
# ==========================================================
# MULTIPLE SEARCHES (APIFY STYLE)
# ==========================================================

def generate_search_queries(config):

    search_strings = config.get(
        "searchStringsArray",
        ["restaurant"]
    )

    location = (
        config.get("locationQuery", "")
        or ""
    ).strip()

    category_filters = config.get(
        "categoryFilterWords",
        []
    )

    search_matching = (
        config.get(
            "searchMatching",
            "all"
        )
        or "all"
    ).lower()

    default_keywords = [

        "restaurant",
        "cafe",
        "coffee shop",
        "fast food",
        "bistro",
        "steakhouse",
        "grill",
        "seafood restaurant",
        "asian restaurant",
        "thai restaurant",
        "japanese restaurant",
        "korean restaurant",
        "mexican restaurant",
        "vegetarian restaurant",
        "brunch restaurant"

    ]

    expanded_keywords = config.get(
        "expandedKeywords",
        default_keywords
    )

    queries = []

    # ---------------------------------------------
    # Original search strings
    # ---------------------------------------------

    for search in search_strings:

        search = clean_text(search)

        if not search:
            continue

        if location:
            queries.append(
                f"{search} in {location}"
            )
        else:
            queries.append(search)

    # ---------------------------------------------
    # Category Filters
    # ---------------------------------------------

    for category in category_filters:

        category = clean_text(category)

        if not category:
            continue

        if location:
            queries.append(
                f"{category} in {location}"
            )
        else:
            queries.append(category)

    # ---------------------------------------------
    # Automatic Expansion
    # ---------------------------------------------

    if search_matching == "all":

        for keyword in expanded_keywords:

            keyword = clean_text(keyword)

            if not keyword:
                continue

            if location:
                queries.append(
                    f"{keyword} in {location}"
                )
            else:
                queries.append(keyword)

    # ---------------------------------------------
    # Remove duplicates
    # ---------------------------------------------

    unique_queries = []
    seen = set()

    for query in queries:

        key = query.lower()

        if key in seen:
            continue

        seen.add(key)

        unique_queries.append(query)

    log(
        f"Generated {len(unique_queries)} search queries."
    )

    return unique_queries


# ==========================================================
# GOOGLE COOKIE POPUP
# ==========================================================

def close_cookie_dialog(page):

    selectors = [

        'button:has-text("Accept all")',
        'button:has-text("Accept")',
        'button:has-text("I agree")',
        'button:has-text("Agree")',
        'button:has-text("OK")',
        'button:has-text("Got it")',

        'button[aria-label="Accept all"]',
        'button[aria-label="Accept"]',

        'form button',

        '[role="dialog"] button',

    ]

    for selector in selectors:

        try:

            buttons = page.locator(selector)

            count = min(
                buttons.count(),
                5
            )

            for i in range(count):

                button = buttons.nth(i)

                if not button.is_visible():
                    continue

                text = safe_text(button).lower()

                if text:

                    if any(word in text for word in [
                        "accept",
                        "agree",
                        "ok",
                        "got it"
                    ]):

                        button.click(force=True)

                        page.wait_for_timeout(1000)

                        log(
                            "Cookie dialog closed."
                        )

                        return

                else:

                    button.click(force=True)

                    page.wait_for_timeout(1000)

                    return

        except Exception:

            continue

# ==========================================================
# BASIC PLACE INFO
# ==========================================================

def extract_name(page):

    selectors = [

        "h1.DUwDvf",
        "h1.fontHeadlineLarge",
        "h1",

    ]

    for selector in selectors:

        try:

            locator = page.locator(selector).first

            if locator.count():

                text = safe_text(locator)

                if text:

                    return text

        except:
            pass

    return ""


# ==========================================================
# ADDRESS
# ==========================================================

def extract_address(page):

    selectors = [

        'button[data-item-id="address"]',
        'button[data-tooltip="Copy address"]',
        'button[aria-label*="Address"]',
        'button[aria-label*="address"]',
        '[data-item-id="address"]',
        '[aria-label*="Address"]'

    ]

    for selector in selectors:

        try:

            locator = page.locator(selector).first

            if locator.count():

                text = safe_text(locator)

                if text:

                    text = text.replace("Address:", "").strip()

                    return text

        except:
            pass

    return ""


# ==========================================================
# PHONE
# ==========================================================

def extract_phone(page):

    selectors = [

        'button[data-item-id*="phone"]',
        'button[data-tooltip="Copy phone number"]',
        'button[aria-label*="Phone"]',
        'button[aria-label*="phone"]',
        '[data-item-id*="phone"]'

    ]

    for selector in selectors:

        try:

            locator = page.locator(selector).first

            if locator.count():

                text = safe_text(locator)

                if text:

                    return text

        except:
            pass

    return ""


# ==========================================================
# WEBSITE
# ==========================================================

def extract_website(page):

    selectors = [

        'a[data-item-id="authority"]',
        'a[data-tooltip="Open website"]',
        'a[aria-label*="Website"]',
        'a[aria-label*="website"]',
        'a[data-item-id*="authority"]'

    ]

    for selector in selectors:

        try:

            locator = page.locator(selector).first

            if locator.count():

                href = safe_attribute(locator, "href")

                if href and href.startswith("http"):

                    return href

        except:
            pass

    return ""


# ==========================================================
# CATEGORY
# ==========================================================

def extract_category(page):

    selectors = [

        "button.DkEaL",
        "button[jsaction*='category']",
        "button:near(h1)",
        "div.DkEaL",
        "span.DkEaL"

    ]

    for selector in selectors:

        try:

            locators = page.locator(selector)

            total = min(locators.count(), 10)

            for i in range(total):

                text = safe_text(locators.nth(i))

                if not text:
                    continue

                if len(text) > 60:
                    continue

                if any(word in text.lower() for word in [

                    "restaurant",
                    "cafe",
                    "coffee",
                    "bakery",
                    "hotel",
                    "fast food",
                    "bistro",
                    "grill"


                ]):

                    return text

        except:
            pass

    return ""


# ==========================================================
# RATING
# ==========================================================

def extract_rating(page):

    selectors = [

        "div.F7nice span",
        "span.ceNzKf",
        "div.fontDisplayLarge",
        '[role="img"]',
        '[aria-label*="stars"]'

    ]

    for selector in selectors:

        try:

            locators = page.locator(selector)

            total = min(locators.count(), 5)

            for i in range(total):

                text = safe_text(locators.nth(i))

                if not text:

                    text = safe_attribute(
                        locators.nth(i),
                        "aria-label"
                    )

                match = re.search(r"\d\.\d", text)

                if match:

                    return match.group(0)

        except:
            pass

    return ""


# ==========================================================
# REVIEWS COUNT
# ==========================================================

def extract_reviews_count(page):

    selectors = [

        "button[aria-label*='review']",
        "span[aria-label*='review']",
        "div.fontBodySmall",
        '[aria-label*="reviews"]'

    ]

    for selector in selectors:

        try:

            locators = page.locator(selector)

            total = min(locators.count(), 10)

            for i in range(total):

                text = safe_text(locators.nth(i))

                if not text:

                    text = safe_attribute(
                        locators.nth(i),
                        "aria-label"
                    )

                if "review" not in text.lower():

                    continue

                match = re.search(r'([\d,]+)', text)

                if match:

                    return match.group(1).replace(",", "")

        except:
            pass

    return ""

# ==========================================================
# PRICE RANGE
# ==========================================================

def extract_price(page):

    selectors = [

        "span",
        "div",
        "button"

    ]

    currencies = [

        "$",
        "€",
        "£",
        "₹",
        "₨",
        "CHF"

    ]

    try:

        for selector in selectors:

            elements = page.locator(selector)

            total = min(
                elements.count(),
                300
            )

            for i in range(total):

                text = safe_text(
                    elements.nth(i)
                )

                if not text:
                    continue

                if len(text) > 25:
                    continue

                if any(
                    symbol in text
                    for symbol in currencies
                ):

                    return text

    except Exception:

        pass

    return ""
# ==========================================================
# OPEN STATUS
# ==========================================================

def extract_open_status(page):

    selectors = [

        '[jsaction*="pane.openhours"] span',
        '[jsaction*="pane.hours"] span',
        'div[aria-label*="Hours"] span',
        "span.ZDu9vd span",
        "div.o0Svhf span",
        '[role="main"] span',
        "span"

    ]

    keywords = [

        "open",
        "closed",
        "opens",
        "closes",
        "temporarily closed"

    ]

    for selector in selectors:

        try:

            elements = page.locator(selector)

            total = min(elements.count(), 120)

            for i in range(total):

                text = safe_text(elements.nth(i))

                if not text:
                    continue

                lower = text.lower()

                if any(word in lower for word in keywords):

                    return text

        except Exception:
            pass

    return ""


# ==========================================================
# WEEKLY HOURS
# ==========================================================

def extract_weekly_hours(page):

    hours = []

    try:

        button = page.locator(
            '[jsaction*="pane.openhours"]'
        ).first

        if button.count():

            button.click(force=True)

            page.wait_for_timeout(1200)

    except Exception:
        pass

    selectors = [

        "table tr",
        "table tbody tr",
        '[role="dialog"] table tr',
        'div[role="dialog"] table tr'

    ]

    week_days = [

        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"

    ]

    for selector in selectors:

        try:

            rows = page.locator(selector)

            total = rows.count()

            if total == 0:
                continue

            for i in range(total):

                text = safe_text(rows.nth(i))

                if not text:
                    continue

                if any(day in text for day in week_days):

                    if text not in hours:

                        hours.append(text)

            if hours:
                break

        except Exception:
            pass

    return hours


# ==========================================================
# MAIN PHOTO
# ==========================================================

def extract_photo_url(page):

    try:

        images = page.locator("img")

        total = min(images.count(), 150)

        best = ""

        for i in range(total):

            src = safe_attribute(
                images.nth(i),
                "src"
            )

            if not src:
                continue

            if "googleusercontent.com" not in src:
                continue

            replacements = {

                "=w32": "=w1200",
                "=w64": "=w1200",
                "=w96": "=w1200",
                "=w128": "=w1200",
                "=w256": "=w1200",
                "=s32": "=s1200",
                "=s64": "=s1200",
                "=s96": "=s1200"

            }

            for old, new in replacements.items():

                src = src.replace(old, new)

            best = src

            if "1200" in src:

                return src

        return best

    except Exception:

        return ""


# ==========================================================
# REVIEW BREAKDOWN
# ==========================================================

def extract_review_breakdown(page):

    breakdown = {

        "5": "",
        "4": "",
        "3": "",
        "2": "",
        "1": ""

    }

    selectors = [

        "tr.BHOKXe",
        '[aria-label*="stars"]',
        '[role="img"][aria-label*="stars"]'

    ]

    for selector in selectors:

        try:

            rows = page.locator(selector)

            total = rows.count()

            if total == 0:
                continue

            for i in range(total):

                label = safe_attribute(
                    rows.nth(i),
                    "aria-label"
                )

                if not label:
                    continue

                match = re.search(

                    r'(\d)\s*stars?,?\s*([\d,]+)',

                    label

                )

                if match:

                    breakdown[match.group(1)] = match.group(2)

            if any(breakdown.values()):
                break

        except Exception:
            pass

    return breakdown
# ==========================================================
# REVIEWS
# ==========================================================

def scroll_reviews(page, max_reviews=5):

    if max_reviews <= 0:
        return

    try:

        container = page.locator('div[role="feed"]').first

        if not container.count():
            return

        scrolls = max(4, min(max_reviews, 25))

        for _ in range(scrolls):

            container.evaluate(
                "(el)=>el.scrollBy(0,2500)"
            )

            page.wait_for_timeout(350)

    except Exception:

        pass


def extract_reviews(
    page,
    max_reviews=5,
    personal_data=True
):

    reviews = []

    if max_reviews <= 0:
        return reviews

    scroll_reviews(page, max_reviews)

    try:

        cards = page.locator("div.jftiEf")

        total = min(cards.count(), max_reviews)

        for i in range(total):

            card = cards.nth(i)

            try:

                more = card.locator(
                    'button:has-text("More")'
                )

                if more.count():

                    more.first.click(force=True)

                    page.wait_for_timeout(150)

            except:
                pass

            review = {

                "reviewer": "",
                "rating": "",
                "time": "",
                "text": "",
                "reviewer_profile": "",
                "owner_response": "",
                "images": []

            }

            if personal_data:

                for selector in [

                    ".d4r55",
                    ".TSUbDb",
                    "button"

                ]:

                    try:

                        txt = safe_text(
                            card.locator(selector).first
                        )

                        if txt:

                            review["reviewer"] = txt
                            break

                    except:
                        pass

                try:

                    review["reviewer_profile"] = safe_attribute(
                        card.locator("a").first,
                        "href"
                    )

                except:
                    pass

            try:

                review["rating"] = safe_attribute(
                    card.locator('[role="img"]').first,
                    "aria-label"
                )

            except:
                pass

            for selector in [

                ".rsqaWe",
                ".DU9Pgb",
                "span"

            ]:

                try:

                    txt = safe_text(
                        card.locator(selector).first
                    )

                    if txt:

                        review["time"] = txt
                        break

                except:
                    pass

            for selector in [

                ".wiI7pd",
                ".MyEned",
                ".jJc9Ad"

            ]:

                try:

                    txt = safe_text(
                        card.locator(selector).first
                    )

                    if txt:

                        review["text"] = txt
                        break

                except:
                    pass

            try:

                response = safe_text(
                    card.locator(".CDe7pd").first
                )

                review["owner_response"] = response

            except:
                pass

            try:

                imgs = card.locator("img")

                img_total = imgs.count()

                for j in range(img_total):

                    src = safe_attribute(
                        imgs.nth(j),
                        "src"
                    )

                    if src and "googleusercontent.com" in src:

                        if src not in review["images"]:

                            review["images"].append(src)

            except:
                pass

            reviews.append(review)

    except Exception:

        pass

    return reviews


# ==========================================================
# RESULTS PANEL
# ==========================================================

def wait_for_results_panel(page):

    selectors = [

        'div[role="feed"]',
        'div.m6QErb',
        'div[aria-label*="Results"]',
        'div[aria-label*="Search results"]'

    ]

    for selector in selectors:

        try:

            page.wait_for_selector(
                selector,
                timeout=15000
            )

            return selector

        except:
            pass

    return None


# ==========================================================
# INFINITE SCROLL (APIFY STYLE)
# ==========================================================

def scroll_results_panel(
    page,
    panel_selector,
    max_places
):

    collected = set()

    previous = 0

    no_change = 0

    scrolls = 0

    panel = page.locator(panel_selector)

    while len(collected) < max_places:

        cards = page.locator("a.hfpxzc")

        total = cards.count()

        if total:

            try:

                cards.nth(total-1).scroll_into_view_if_needed()

            except:
                pass

        page.wait_for_timeout(250)

        for i in range(total):

            try:

                href = cards.nth(i).get_attribute("href")

                if not href:
                    continue

                if "/place/" not in href:
                    continue

                href = href.split("&")[0]

                collected.add(href)

            except:
                pass

        log(f"URLs Found : {len(collected)}")

        if len(collected) >= max_places:

            break

        if len(collected) == previous:

            no_change += 1

        else:

            no_change = 0

        previous = len(collected)

        if no_change >= 20:

            log("End of results reached.")

            break

        try:

            panel.evaluate(
                "(el)=>el.scrollBy(0,6000)"
            )

        except:

            page.mouse.wheel(
                0,
                6000
            )

        scrolls += 1

        page.wait_for_timeout(450)

        if scrolls % 12 == 0:

            page.wait_for_timeout(1500)

    return list(collected)

# ==========================================================
# COLLECT PLACE URLS
# ==========================================================

def collect_place_urls(page, config):

    search_query = build_search_query(config)

    log(f"Searching: {search_query}")

    close_cookie_dialog(page)

    search_box = page.locator(
        'input[name="q"]'
    )

    search_box.wait_for(
        state="visible",
        timeout=30000
    )

    try:

        search_box.click()

    except:

        search_box.click(force=True)

    # Completely clear previous query

    search_box.press("Control+A")

    search_box.press("Delete")

    search_box.fill("")

    page.keyboard.type(
        search_query,
        delay=15
    )

    page.keyboard.press("Enter")

    wait_for_page(page)

    page.wait_for_timeout(2500)

    panel = wait_for_results_panel(page)

    if panel is None:

        log("Results panel not found.")

        return []

    page.wait_for_timeout(1500)

    max_places = config.get(

        "maxCrawledPlacesPerSearch",

        500

    )

    urls = scroll_results_panel(

        page,

        panel,

        max_places

    )

    # =====================================================
    # Retry 1
    # =====================================================

    if len(urls) < min(50, max_places):

        log("Retry 1...")

        page.wait_for_timeout(2500)

        urls2 = scroll_results_panel(

            page,

            panel,

            max_places

        )

        urls = list(dict.fromkeys(urls + urls2))

    # =====================================================
    # Retry 2
    # =====================================================

    if len(urls) < min(100, max_places):

        log("Retry 2 (Deep Scan)...")

        try:

            page.locator(panel).evaluate(
                "(el)=>el.scrollTo(0,0)"
            )

            page.wait_for_timeout(1000)

            page.locator(panel).evaluate(
                "(el)=>el.scrollTo(0,el.scrollHeight)"
            )

            page.wait_for_timeout(3000)

        except:

            pass

        urls3 = scroll_results_panel(

            page,

            panel,

            max_places

        )

        urls = list(dict.fromkeys(urls + urls3))

    log(f"Collected {len(urls)} unique URLs.")

    return urls


# ==========================================================
# SCRAPE SINGLE PLACE
# ==========================================================

def scrape_place(page, url, config):

    page.goto(
        url,
        timeout=60000,
        wait_until="domcontentloaded"
    )

    wait_after_open(page)

    place = {
        "url": url,
        "place_id": extract_place_id(url),
        "latitude": extract_latitude(url),
        "longitude": extract_longitude(url),
        "name": extract_name(page),
        "category": extract_category(page),
        "rating": extract_rating(page),
        "reviews_count": extract_reviews_count(page),
        "price_range": extract_price(page),
        "address": extract_address(page),
        "website": extract_website(page),
        "phone": extract_phone(page),
        "opening_status": "",
        "weekly_hours": [],
        "photo_url": "",
        "review_breakdown": {},
        "top_reviews": []
    }

    if config.get("scrapePlaceDetailPage", True):
        try:
            place["opening_status"] = extract_open_status(page)
        except Exception:
            pass

        try:
            place["weekly_hours"] = extract_weekly_hours(page)
        except Exception:
            pass

    if config.get("maxImages", 0) > 0:
        try:
            place["photo_url"] = extract_photo_url(page)
        except Exception:
            pass

    try:
        place["review_breakdown"] = extract_review_breakdown(page)
    except Exception:
        pass

    max_reviews = config.get("maxReviews", 0)

    if max_reviews > 0:
        try:
            place["top_reviews"] = extract_reviews(
                page,
                max_reviews=max_reviews,
                personal_data=config.get("scrapeReviewsPersonalData", True)
            )
        except Exception:
            pass

    log("")
    log("=" * 65)
    log(place["name"])
    log("-" * 65)
    log(f"Category      : {place['category']}")
    log(f"Rating        : {place['rating']}")
    log(f"Reviews       : {place['reviews_count']}")
    log(f"Price         : {place['price_range']}")
    log(f"Address       : {place['address']}")
    log(f"Website       : {place['website']}")
    log(f"Phone         : {place['phone']}")

    if place["opening_status"]:
        log(f"Open          : {place['opening_status']}")

    if place["photo_url"]:
        log("Photo         : YES")
    else:
        log("Photo         : NO")

    log(f"Top Reviews   : {len(place['top_reviews'])}")

    return place


# ==========================================================
# SAVE JSON
# ==========================================================

def save_json(results):

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    log("JSON saved -> results.json")


# ==========================================================
# SAVE CSV
# ==========================================================

def save_csv(results):

    if not results:
        return

    rows = []

    for place in results:
        row = place.copy()
        row["weekly_hours"] = " | ".join(place.get("weekly_hours", []))
        row["review_breakdown"] = json.dumps(place.get("review_breakdown", {}), ensure_ascii=False)
        row["top_reviews"] = json.dumps(place.get("top_reviews", []), ensure_ascii=False)
        rows.append(row)

    headers = rows[0].keys()

    with open("results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    log("CSV saved -> results.csv")


# ==========================================================
# MAIN CRAWLER
# ==========================================================

def test_google_maps(config):

    results = []
    failed = 0

    log("Opening Google Maps...")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=config.get("headless", False),
            args=[
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            locale="en-US"
        )

        page = context.new_page()

        page.goto(
            "https://www.google.com/maps",
            timeout=60000
        )

        wait_for_page(page)

        close_cookie_dialog(page)

        # ==================================================
        # MULTI SEARCH
        # ==================================================

        all_urls = set()

        search_queries = generate_search_queries(config)

        log("")
        log("=" * 70)
        log(f"Running {len(search_queries)} search queries")
        log("=" * 70)

        max_total = config.get(
            "maxCrawledPlacesPerSearch",
            500
        )

        for index, query in enumerate(search_queries):

            if len(all_urls) >= max_total:

                log("Maximum requested URLs reached.")

                break

            log("")
            log(f"Search {index+1}/{len(search_queries)}")
            log(query)

            page.goto(
                "https://www.google.com/maps",
                timeout=60000
            )

            wait_for_page(page)

            close_cookie_dialog(page)

            temp = config.copy()

            temp["customSearchQuery"] = query

            temp["maxCrawledPlacesPerSearch"] = (
                max_total - len(all_urls)
            )

            urls = collect_place_urls(
                page,
                temp
            )

            before = len(all_urls)

            all_urls.update(urls)

            added = len(all_urls) - before

            log(f"New URLs Added : {added}")
            log(f"Total Unique URLs : {len(all_urls)}")

        urls = list(all_urls)

        total_urls = len(urls)

        if total_urls == 0:

            log("No URLs found.")

            browser.close()

            return

        log("")
        log("=" * 70)
        log(f"TOTAL UNIQUE URLS : {total_urls}")
        log("=" * 70)

        # ==================================================
        # SCRAPE
        # ==================================================

        for index, url in enumerate(urls):

            try:

                log("")
                log("=" * 70)
                log(f"Scraping {index+1}/{total_urls}")

                place = scrape_place(
                    page,
                    url,
                    config
                )

                if place:

                    results.append(place)

            except Exception as e:

                failed += 1

                error(str(e))

        save_json(results)

        save_csv(results)

        browser.close()

    # ======================================================
    # SUMMARY
    # ======================================================

    elapsed = round(
        time.time() - START_TIME,
        2
    )

    average = 0

    if results:

        average = round(
            elapsed / len(results),
            2
        )

    log("")
    log("=" * 70)
    log("CRAWLER SUMMARY")
    log("=" * 70)

    log(f"Search Query   : {build_search_query(config)}")
    log(f"Location       : {config.get('locationQuery')}")
    log(f"URLs Found     : {total_urls}")
    log(f"URLs Scraped   : {len(results)}")
    log(f"Failed         : {failed}")
    log(f"Elapsed Time   : {elapsed} sec")
    log(f"Average/Place  : {average} sec")
    log(f"Items Exported : {len(results)}")
    log(f"Memory Usage   : {get_memory_usage()} MB")
    log(f"CPU Usage      : {get_cpu_usage()} %")

    log("=" * 70)
            