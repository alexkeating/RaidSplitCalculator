import os
import jsonpickle
from shutil import copyfile

from raid import *


class RaidDB:
    raid_db: RaidDict = {}
    db_path = os.getenv("DB_PATH")
    db_backup_path = db_path + '.bckp'

    def __del__(self):
        self.close()

    def __init__(self):
        if os.path.isfile(self.db_backup_path):
            raise IOError("Backup file exists already. Last time, Something went wrong ")

        try:
            # backup the db and open
            copyfile(self.db_path, self.db_backup_path)
            file = open(self.db_path)
        except IOError:
            # If db not exists, create the file and populate with an empty dict
            file = open(self.db_path, 'w+')
            file.write(" {}")
            file.close()

            # backup the db and open
            copyfile(self.db_path, self.db_backup_path)
            file = open(self.db_path)

        self.raid_db = jsonpickle.decode(file.read())

    def store(self, raid_name: str, raid: Raid):
        self.raid_db[raid_name] = raid

    def find_raid(self, raid_name: str) -> Raid:
        raid_name = raid_name.strip()
        return self.raid_db.get(raid_name)

    def close(self):
        file = open(self.db_path, 'w')
        file.write(jsonpickle.encode(self.raid_db))
        os.remove(self.db_backup_path)
