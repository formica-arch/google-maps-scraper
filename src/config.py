import json
import os


DEFAULT_CONFIG = {

    "searchStringsArray": ["restaurant"],
    "locationQuery": "New York",
    "maxCrawledPlacesPerSearch": 50,
    "language": "en",

    "categoryFilterWords": [],
    "searchMatching": "all",

    "placeMinimumStars": "",

    "website": "allPlaces",

    "skipClosedPlaces": False,

    "scrapePlaceDetailPage": True,

    "scrapeDirectories": False,

    "maxQuestions": 0,

    "maxReviews": 5,

    "reviewsSort": "newest",

    "reviewsFilterString": "",

    "reviewsOrigin": "all",

    "scrapeReviewsPersonalData": True,

    "maxImages": 1,

    "scrapeImageAuthors": False
}


def load_input():

    paths = [

        "input.json",

        os.path.join("apify_storage", "key_value_stores", "default", "INPUT.json")

    ]

    for path in paths:

        if not os.path.exists(path):
            continue

        try:

            with open(path, "r", encoding="utf-8") as f:

                data = json.load(f)

            config = DEFAULT_CONFIG.copy()

            config.update(data)

            return config

        except Exception:

            continue

    return DEFAULT_CONFIG.copy()