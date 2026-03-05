"""YAML configuration loader and validation."""

from pathlib import Path
import yaml


# Default values for optional config keys
DEFAULTS = {
    'site': {
        'language': 'es',
        'country': 'AR',
        'template': 'starter',
    },
    'content': {
        'articles_on_homepage': 20,
        'max_description_length': 250,
        'max_article_age_days': 30,
    },
}

REQUIRED_SITE_KEYS = ['title', 'url']


def load_config(config_path):
    """Load and validate a site.yaml configuration file.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        dict with validated configuration.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If required keys are missing.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError("Config file is empty")

    # Validate required sections
    if 'site' not in config:
        raise ValueError("Missing required section: 'site'")

    # Validate required site keys
    for key in REQUIRED_SITE_KEYS:
        if key not in config['site']:
            raise ValueError(f"Missing required site key: '{key}'")

    # Apply defaults
    for section, defaults in DEFAULTS.items():
        if section not in config:
            config[section] = {}
        for key, value in defaults.items():
            config[section].setdefault(key, value)

    # Ensure sources list exists
    if 'sources' not in config:
        config['sources'] = []

    return config
