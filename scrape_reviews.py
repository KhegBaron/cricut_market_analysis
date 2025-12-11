import csv
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# --------------- AMAZON SCRAPER --------------- #

def scrape_amazon_reviews(product_url, max_pages=5, sleep_seconds=2):
    """
    Scrape reviews from an Amazon product page or product-reviews page.
    Returns a list of dicts: [{'rating': 5, 'title': ..., 'date': ..., 'body': ...}, ...]
    """

    reviews = []
    session = requests.Session()
    session.headers.update(HEADERS)

    print("[AMAZON] Preparing reviews URL...")

    # If user gave a /product-reviews/ URL directly, use it as the base
    if "product-reviews" in product_url:
        # Strip any existing pageNumber parameter so we can add our own
        if "&pageNumber=" in product_url:
            base_reviews_url = product_url.split("&pageNumber=")[0]
        else:
            base_reviews_url = product_url
    else:
        # Otherwise, try to extract ASIN from a /dp/ style URL and build reviews URL
        asin = None
        if "/dp/" in product_url:
            asin = product_url.split("/dp/")[1].split("/")[0]
        elif "/product/" in product_url:
            asin = product_url.split("/product/")[1].split("/")[0]

        if not asin:
            print("[AMAZON] Could not extract ASIN from URL. Use a /dp/... link or a product-reviews URL.")
            return reviews

        parsed = urlparse(product_url)
        base_reviews_url = f"{parsed.scheme}://{parsed.netloc}/product-reviews/{asin}?reviewerType=all_reviews"

    print(f"[AMAZON] Base reviews URL: {base_reviews_url}")

    for page in range(1, max_pages + 1):
        # Ensure we add pageNumber correctly
        if "pageNumber=" in base_reviews_url:
            page_url = base_reviews_url.split("pageNumber=")[0].rstrip("&?") + f"&pageNumber={page}"
        else:
            join_char = "&" if "?" in base_reviews_url else "?"
            page_url = f"{base_reviews_url}{join_char}pageNumber={page}"

        print(f"[AMAZON] Fetching review page {page}: {page_url}")

        resp = session.get(page_url)
        if resp.status_code != 200:
            print(f"[AMAZON] Stopping; status code {resp.status_code}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        review_divs = soup.select("div[data-hook='review']")
        if not review_divs:
            print("[AMAZON] No reviews found on this page; stopping.")
            break

        for div in review_divs:
            # Rating
            rating_tag = div.select_one("i[data-hook='review-star-rating'] span")
            if not rating_tag:
                rating_tag = div.select_one("i[data-hook='cmps-review-star-rating'] span")
            rating_text = rating_tag.get_text(strip=True) if rating_tag else ""
            rating_value = None
            if rating_text:
                try:
                    rating_value = float(rating_text.split()[0])
                except Exception:
                    rating_value = None

            # Title
            title_tag = div.select_one("a[data-hook='review-title'] span")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Date
            date_tag = div.select_one("span[data-hook='review-date']")
            date_text = date_tag.get_text(strip=True) if date_tag else ""

            # Body
            body_tag = div.select_one("span[data-hook='review-body'] span")
            if not body_tag:
                body_tag = div.select_one("span[data-hook='review-body']")
            body = body_tag.get_text(" ", strip=True) if body_tag else ""

            reviews.append(
                {
                    "platform": "amazon",
                    "rating": rating_value,
                    "title": title,
                    "date": date_text,
                    "body": body,
                }
            )

        time.sleep(sleep_seconds)

    print(f"[AMAZON] Collected {len(reviews)} reviews.")
    return reviews

# --------------- MICHAELS SCRAPER --------------- #

def scrape_michaels_reviews(product_url, max_pages=5, sleep_seconds=2):
    """
    Scrape reviews from a Michaels product page.
    NOTE: The exact HTML structure may change. You might need to tweak CSS selectors
    after inspecting the page source in your browser.
    """
    reviews = []
    session = requests.Session()
    session.headers.update(HEADERS)

    current_url = product_url

    for page in range(1, max_pages + 1):
        print(f"[MICHAELS] Fetching page {page}: {current_url}")
        resp = session.get(current_url)
        if resp.status_code != 200:
            print(f"[MICHAELS] Stopping; status code {resp.status_code}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # These selectors are examples; inspect your target page and adjust:
        review_blocks = soup.select("div.review, div.bv-content-review, div.pr-review")

        if not review_blocks:
            print("[MICHAELS] No review blocks found. You may need to adjust selectors.")
            break

        for block in review_blocks:
            rating_value = None
            rating_tag = block.select_one("meta[itemprop='ratingValue']")
            if rating_tag and rating_tag.get("content"):
                try:
                    rating_value = float(rating_tag["content"])
                except Exception:
                    pass

            if rating_value is None:
                rating_text_tag = block.find(string=lambda s: s and "out of 5" in s)
                if rating_text_tag:
                    try:
                        rating_value = float(rating_text_tag.strip().split()[0])
                    except Exception:
                        rating_value = None

            title_tag = block.select_one("h3, h4, .review-title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            date_tag = block.select_one("time, .review-date")
            date_text = date_tag.get_text(strip=True) if date_tag else ""

            body_tag = block.select_one(".review-text, .bv-content-summary-body-text, p")
            body = body_tag.get_text(" ", strip=True) if body_tag else ""

            reviews.append(
                {
                    "platform": "michaels",
                    "rating": rating_value,
                    "title": title,
                    "date": date_text,
                    "body": body,
                }
            )

        next_link = soup.find("a", string=lambda s: s and "Next" in s)
        if not next_link or not next_link.get("href"):
            print("[MICHAELS] No next page link found; stopping.")
            break

        next_href = next_link["href"]
        if next_href.startswith("http"):
            current_url = next_href
        else:
            parsed = urlparse(product_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            current_url = base + next_href

        time.sleep(sleep_seconds)

    print(f"[MICHAELS] Collected {len(reviews)} reviews.")
    return reviews

# --------------- MAIN DISPATCH + CSV SAVE --------------- #

def save_reviews_to_csv(reviews, filename="reviews_output.csv"):
    if not reviews:
        print("No reviews to save.")
        return

    fieldnames = ["platform", "rating", "title", "date", "body"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in reviews:
            writer.writerow(r)

    print(f"Saved {len(reviews)} reviews to {filename}")

def scrape_reviews(product_url, max_pages=5, output_file="reviews_output.csv"):
    domain = urlparse(product_url).netloc.lower()

    if "amazon." in domain:
        reviews = scrape_amazon_reviews(product_url, max_pages=max_pages)
    elif "michaels.com" in domain:
        reviews = scrape_michaels_reviews(product_url, max_pages=max_pages)
    else:
        print(f"Unsupported domain: {domain}")
        return

    save_reviews_to_csv(reviews, output_file)

if __name__ == "__main__":
    # You can use either:
    # - an Amazon product page URL with /dp/...
    # - OR an Amazon product-reviews URL like the one you have
    product_url = "https://www.amazon.com/product-reviews/B0DVWCD3P7/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews"

    scrape_reviews(
        product_url=product_url,
        max_pages=3,          # small while testing
        output_file="reviews_output.csv"
    )
