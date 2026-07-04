"""
Input loader for Apify-compatible configuration.
Loads configuration from input.json and merges with defaults.
"""

import json
import os
from src.config import DEFAULT_CONFIG


def load_input():
    """
    Load configuration from input.json.
    Merges with defaults from config.py.
    
    Returns:
        dict: Complete configuration object
    """
    apify_storage_dir = os.getenv("APIFY_LOCAL_STORAGE_DIR", "/apify_storage")
    input_candidates = [
        os.path.join(apify_storage_dir, "key_value_stores", "default", "INPUT.json"),
        "input.json"
    ]
    config = DEFAULT_CONFIG.copy()
    
    # Try Apify input first, then local input.json
    for input_file in input_candidates:
        if not os.path.exists(input_file):
            continue

        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    # Merge with defaults
                    config.update(data)
                    break
        except json.JSONDecodeError:
            print(f"[WARNING] {input_file} is empty or invalid. Trying next input source.")
        except Exception as e:
            print(f"[WARNING] Error loading {input_file}: {e}. Trying next input source.")
    
    return config


def validate_config(config):
    """
    Validate that required configuration fields are present.
    
    Args:
        config (dict): Configuration object
    
    Returns:
        bool: True if valid
    
    Raises:
        ValueError: If required fields are missing
    """
    required_fields = [
        "searchStringsArray",
        "locationQuery",
        "maxCrawledPlacesPerSearch"
    ]
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")
    
    return True
