import os
import logging
import sys
from bot_commands import bot


def main():
    token = os.getenv("API_TOKEN")
    if token is None:
        sys.exit("Environment variable API_TOKEN must be supplied")

    db_path = os.getenv("DB_PATH")
    if db_path is None:
        sys.exit("Environment variable DB_PATH must be supplied")

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting RaidSplitBot")

    bot.run(token)


if __name__ == "__main__":
    main()
