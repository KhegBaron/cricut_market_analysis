import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer

print("Loading reviews...")
input_file = "reviews_output.csv"
df = pd.read_csv(input_file)
df["body"] = df["body"].fillna("")

print("Initializing VADER...")
sia = SentimentIntensityAnalyzer()

print("Scoring sentiment...")
scores = df["body"].apply(lambda text: sia.polarity_scores(str(text)))

df["neg"] = scores.apply(lambda d: d["neg"])
df["neu"] = scores.apply(lambda d: d["neu"])
df["pos"] = scores.apply(lambda d: d["pos"])
df["compound"] = scores.apply(lambda d: d["compound"])

# Sentiment Labeling
def label_sentiment(c):
    if c >= 0.2:
        return "positive"
    elif c <= -0.2:
        return "negative"
    else:
        return "neutral"

df["sentiment_label"] = df["compound"].apply(label_sentiment)

print("Tagging aspects...")

SOFTWARE_WORDS = [
      # General software
    "software", "app", "application", "firmware", "update", "bug",
    "crash", "freezes", "freeze", "lag", "laggy", "slow", "performance",
    "install", "installing", "installation", "download", "loading", "load",
    "error", "popup", "message",
    
    # Cricut Design Space specific
    "design space", "cloud", "online only", "offline", "subscription",
    "membership", "account", "sign in", "login",

    # Connectivity issues
    "connect", "connection", "connectivity", "bluetooth", "wifi", "wireless",
    "pair", "paired", "pairing", "usb", "driver", "sync",
    
    # Editing tools / usability
    "font", "template", "template library", "project library", "preview",
    "render", "export", "import", "saving", "save failed", "resize",
    "alignment tools", "weld", "slice", "cut path"
]

HARDWARE_WORDS = [
    # Machine parts
    "machine", "blade", "blades", "knife", "housing", "cutter", "cutting",
    "motor", "roller", "rollers", "roller bar", "sensor", "scan", "feed",
    "pressure", "alignment", "calibration", "jam", "jams", "jamming",
    "print then cut", "ptc", "tracking", "carriage", "belt", "gear",
    
    # Wear & tear
    "break", "broken", "broke", "stuck", "malfunction", "defective",
    
    # Power / connectivity to hardware
    "power", "turn on", "shutoff", "shutting off", "restart",
    "cable", "plug", "cord", "connector",
    
    # Model names — strong hardware indicator
    "maker", "explore", "joy", "cameo", "portrait", "scan n cut",
    "engraving", "debossing", "printing"
]

MATERIALS_WORDS = [
    # Cutting materials
    "vinyl", "mat", "mats", "cardstock", "paper", "material", "materials",
    "iron-on", "iron on", "htv", "heat transfer", "sticker", "adhesive",
    "foil", "fabric", "chipboard", "balsa", "foam", "leather", "glitter",
    
    # Mat issues
    "sticky", "stickiness", "won't stick", "not sticky", "adhesive wore off",
    "replace mat", "scraper",
    
    # Tooling
    "weeding", "weeder", "scraper tool", "scoring", "pen", "markers",
    
    # Material compatibility
    "compatible", "compatibility", "ruined", "tear", "tearing", "rips",
    "cuts too deep", "not deep enough"
]

SUPPORT_WORDS = [
    "customer service", "support", "warranty",
    "help", "return", "refund", "replaced",
    "replacement", "service", "tech support"
]

def classify_aspect(text):
    t = text.lower()
    if any(word in t for word in SOFTWARE_WORDS):
        return "software"
    if any(word in t for word in HARDWARE_WORDS):
        return "hardware"
    if any(word in t for word in MATERIALS_WORDS):
        return "materials"
    if any(word in t for word in SUPPORT_WORDS):
        return "support"
    return "other"

df["aspect"] = df["body"].apply(classify_aspect)

print("Saving detailed sentiment file...")
df.to_csv("reviews_with_sentiment.csv", index=False)


# ===================== BRAND-LEVEL SUMMARY ===================== #

print("Building brand-level summary...")

grouped = df.groupby("brand")
summary = grouped.agg(
    avg_compound=("compound", "mean"),
    avg_rating=("rating", "mean"),
    n_reviews=("brand", "count"),
)

label_counts = df.pivot_table(
    index="brand",
    columns="sentiment_label",
    values="body",
    aggfunc="count",
    fill_value=0,
)

label_perc = label_counts.div(label_counts.sum(axis=1), axis=0)

for col in ["positive", "neutral", "negative"]:
    if col in label_perc.columns:
        summary[f"pct_{col}"] = label_perc[col]
    else:
        summary[f"pct_{col}"] = 0.0

summary.to_csv("brand_sentiment_summary.csv")
print("Saved brand summary.")


# ===================== BRAND + ASPECT SUMMARY ===================== #

print("Building brand-aspect summary...")

aspect_counts = df.pivot_table(
    index=["brand", "aspect"],
    columns="sentiment_label",
    values="body",
    aggfunc="count",
    fill_value=0,
)

aspect_counts["total"] = aspect_counts.sum(axis=1)

for col in ["positive", "neutral", "negative"]:
    if col in aspect_counts.columns:
        aspect_counts[f"pct_{col}"] = aspect_counts[col] / aspect_counts["total"]
    else:
        aspect_counts[f"pct_{col}"] = 0.0

aspect_counts.reset_index().to_csv("brand_aspect_summary.csv", index=False)
print("Saved brand + aspect summary.")

print("=== COMPLETE ===")
print(f"{len(df)} reviews processed.")
