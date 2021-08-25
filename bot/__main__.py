import os
import logging
import sys
from bot_commands import bot


def main():
    TOKEN = os.getenv("API_TOKEN")
    if TOKEN is None:
        sys.exit("Environment variable API_TOKEN must be supplied")

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting RaidSplitBot")

    bot.run(TOKEN)


if __name__ == "__main__":
    main()
