import os
import logging
import sys

from bot_commands import *
import database


def main():
    TOKEN = os.getenv("API_TOKEN")
    if TOKEN is None:
        sys.exit("Environment variable API_TOKEN must be supplied")

    DB_PATH = os.getenv("DB_PATH")
    DB_BACKUP_PATH = DB_PATH + '.bckp'

    database.RAIDS = database.init_db(DB_PATH, DB_BACKUP_PATH)

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting RaidSplitBot")

    bot.run(TOKEN)

    database.close_db(RAIDS, DB_PATH, DB_BACKUP_PATH)

if __name__ == "__main__":
    main()
