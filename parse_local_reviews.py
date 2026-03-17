import csv
import glob
from bs4 import BeautifulSoup

Patterns
BRAND_PATTERNS = {
    "brother": "brother/brother_page_*.html",
    "cricut": "cricut/cricut_page_*.html",
    "silhouette": "silhouette/silhouette_page_*.html",
}

all_reviews = []

for brand, pattern in BRAND_PATTERNS.items():
    filepaths = sorted(glob.glob(pattern))
    if not filepaths:
        print(f"[WARN] No files found for brand '{brand}' with pattern '{pattern}'")
        continue

    for filepath in filepaths:
        print(f"[{brand.upper()}] Processing {filepath}...")
        with open(filepath, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # search for individual review body spans
        body_spans = soup.select("span[data-hook='review-body']")
        print(f"  Found {len(body_spans)} review bodies in this file")

        for body_span in body_spans:
            # Body text
            body = body_span.get_text(" ", strip=True)

            # move upwards in the HTML to find associated rating, title, date
            container = body_span
            # climb up a few levels to search around
            for _ in range(4):
                if container.parent:
                    container = container.parent

            # Rating
            rating = None
            rating_tag = container.find("i", attrs={"data-hook": "review-star-rating"})
            if not rating_tag:
                rating_tag = container.find("i", attrs={"data-hook": "cmps-review-star-rating"})
            if rating_tag and rating_tag.find("span"):
                rating_text = rating_tag.find("span").get_text(strip=True)
                try:
                    rating = float(rating_text.split()[0])
                except Exception:
                    rating = None

            # Title
            title = ""
            title_tag = container.find("a", attrs={"data-hook": "review-title"})
            if title_tag:
                # Sometimes nested span
                span = title_tag.find("span")
                title = (span or title_tag).get_text(strip=True)

            # Date
            date = ""
            date_tag = container.find("span", attrs={"data-hook": "review-date"})
            if date_tag:
                date = date_tag.get_text(strip=True)

            all_reviews.append({
                "brand": brand,
                "platform": "amazon_local_html",
                "rating": rating,
                "title": title,
                "date": date,
                "body": body,
            })

print("\nTotal reviews collected:", len(all_reviews))

output_file = "reviews_output.csv"
if all_reviews:
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["brand", "platform", "rating", "title", "date", "body"]
        )
        writer.writeheader()
        writer.writerows(all_reviews)

    print(f"Saved reviews to {output_file}")
else:
    print("No reviews found in any files. Check that your HTML pages actually show reviews when opened in a browser.")
