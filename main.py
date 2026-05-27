#!/usr/bin/env python3
"""RedditVideoMakerBot - Automatically creates videos from Reddit posts.

This is the main entry point for the bot. It orchestrates the entire
video creation pipeline from fetching Reddit content to rendering the
final video.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Ensure the project root is in the Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.console import print_step, print_substep, handle_exception
from utils.cleanup import cleanup
from utils.ffmpeg_install import ffmpeg_install
from utils import settings

__version__ = "2.0.0"

# Use INFO level to reduce noise in logs; switch to DEBUG when actively debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def check_env() -> bool:
    """Check that all required environment variables and dependencies are set.

    Returns:
        bool: True if all checks pass, False otherwise.
    """
    required_vars = [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(
            "Missing required environment variables: %s", ", ".join(missing)
        )
        logger.error(
            "Please copy .env.template to .env and fill in the required values."
        )
        return False
    return True


def run_bot() -> None:
    """Main bot execution loop.

    Fetches a Reddit post, generates assets (screenshots, TTS audio),
    and renders the final video.
    """
    print_step(f"Starting RedditVideoMakerBot v{__version__}")

    # Load configuration
    config = settings.check_toml(
        "utils/.config.template.toml", "config.toml"
    )
    if config is False:
        logger.error("Configuration file is invalid. Exiting.")
        sys.exit(1)

    # Ensure ffmpeg is available
    ffmpeg_install()

    # Import here to avoid circular imports and allow config to load first
    from reddit.subreddit import get_subreddit_threads
    from video_creation.screenshot_downloader import download_screenshots_of_reddit_posts
    from video_creation.voices import save_text_to_mp3
    from video_creation.background import (
        download_background,
        chop_background_video,
        get_background_config,
    )
    from video_creation.final_video import make_final_video

    reddit_object = get_subreddit_threads(config)
    if not reddit_object:
        logger.error("Could not fetch Reddit thread. Exiting.")
        sys.exit(1)

    print_substep(f"Fetched thread: {reddit_object['thread_title']}", style="bold green")

    # Generate TTS audio
    print_step("Generating text-to-speech audio...")
    length, number_of_comments = save_text_to_mp3(reddit_object)
    print_substep(f"Audio len