from pydantic import BaseModel
from typing import List, Optional


class InputSchema(BaseModel):
    searchStringsArray: List[str]
    locationQuery: str
    maxCrawledPlacesPerSearch: int = 50

    language: str = "en"

    categoryFilterWords: Optional[List[str]] = []

    searchMatching: str = "all"

    placeMinimumStars: Optional[str] = ""

    website: str = "allPlaces"

    skipClosedPlaces: bool = False

    scrapePlaceDetailPage: bool = False

    maxReviews: int = 5

    maxImages: int = 10