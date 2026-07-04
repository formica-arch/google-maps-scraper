"""
Reusable filter functions for validating scraped place dictionaries.
These functions do not import Playwright and only validate place data.
"""


def matches_category(place, config):
    """
    Check if place matches category filter words.
    
    If no filter words are configured, all places pass.
    If filter words are configured, place category must contain at least one.
    
    Args:
        place (dict): Scraped place data
        config (dict): Configuration with 'categoryFilterWords' field
    
    Returns:
        bool: True if place matches filter or no filter configured
    """
    category_filters = config.get("categoryFilterWords", [])
    
    # If no filter configured, accept all
    if not category_filters:
        return True
    
    place_category = place.get("category", "").lower()
    
    # Check if any filter word matches the place category
    for word in category_filters:
        if word.lower() in place_category:
            return True
    
    return False


def matches_rating(place, config):
    """
    Check if place meets minimum rating requirement.
    
    Args:
        place (dict): Scraped place data
        config (dict): Configuration with 'placeMinimumStars' field
    
    Returns:
        bool: True if place rating >= minimum or no minimum configured
    """
    min_stars_str = config.get("placeMinimumStars", "")
    
    # If no minimum configured, accept all
    if not min_stars_str:
        return True
    
    try:
        min_stars = float(min_stars_str)
    except (ValueError, TypeError):
        return True
    
    place_rating_str = place.get("rating", "").strip()
    
    # If place has no rating, reject if minimum is set
    if not place_rating_str:
        return False
    
    try:
        place_rating = float(place_rating_str)
        return place_rating >= min_stars
    except (ValueError, TypeError):
        return False


def matches_open_status(place, config):
    """
    Check if place should be skipped based on open status.
    
    If skipClosedPlaces is True, skip places that are closed.
    
    Args:
        place (dict): Scraped place data
        config (dict): Configuration with 'skipClosedPlaces' field
    
    Returns:
        bool: True if place should be kept
    """
    skip_closed = config.get("skipClosedPlaces", False)
    
    # If not skipping closed places, accept all
    if not skip_closed:
        return True
    
    opening_status = place.get("opening_status", "").lower()
    
    # Skip if status contains "closed"
    if "closed" in opening_status:
        return False
    
    return True


def matches_website(place, config):
    """
    Check if place matches website filter.
    
    Supported modes:
    - "allPlaces": Keep all places
    - "onlyWithWebsite": Skip places without website
    - "onlyWithoutWebsite": Skip places with website
    
    Args:
        place (dict): Scraped place data
        config (dict): Configuration with 'website' field
    
    Returns:
        bool: True if place should be kept
    """
    website_filter = config.get("website", "allPlaces")
    place_website = place.get("website", "").strip()
    
    if website_filter == "allPlaces":
        return True
    elif website_filter == "onlyWithWebsite":
        return bool(place_website)
    elif website_filter == "onlyWithoutWebsite":
        return not bool(place_website)
    
    # Default to allowing all if unknown filter
    return True


def matches_search_query(place, config):
    """
    Check if place matches search query keywords.
    
    Supports two matching modes:
    - "all": All keywords must be found in place name/category
    - "any": At least one keyword must be found
    
    Args:
        place (dict): Scraped place data
        config (dict): Configuration with 'searchStringsArray' and 'searchMatching'
    
    Returns:
        bool: True if place matches search criteria
    """
    search_strings = config.get("searchStringsArray", [])
    search_matching = config.get("searchMatching", "all")
    
    # If no search strings configured, accept all
    if not search_strings:
        return True
    
    place_name = place.get("name", "").lower()
    place_category = place.get("category", "").lower()
    combined_text = f"{place_name} {place_category}".lower()
    
    if search_matching == "all":
        # All keywords must match
        for keyword in search_strings:
            if keyword.lower() not in combined_text:
                return False
        return True
    else:
        # "any" mode: at least one keyword must match
        for keyword in search_strings:
            if keyword.lower() in combined_text:
                return True
        return False


def should_keep_place(place, config):
    """
    Master filter function that applies all enabled filters.
    
    Returns True only if all filters pass.
    
    Args:
        place (dict): Scraped place data
        config (dict): Configuration object with filter settings
    
    Returns:
        bool: True if place should be kept, False if should be filtered out
    """
    if config is None:
        return True
    
    # Apply all filters - place must pass all to be kept
    if not matches_category(place, config):
        return False
    
    if not matches_rating(place, config):
        return False
    
    if not matches_open_status(place, config):
        return False
    
    if not matches_website(place, config):
        return False
    
    if not matches_search_query(place, config):
        return False
    
    return True
