import os
from shutil import copyfile
from database import Database


class LocalFile(Database):
    """
    A simple database solution using a JSON file. The file is stored locally at DB_PATH.
    If no database is present, a new one is created.
    Everytime the file is accessed, a local backup file is created.
    """

    db_path = os.getenv("DB_PATH")
    db_backup_path = db_path + '.bckp'

    def __init__(self):
        if os.path.isfile(self.db_backup_path):
            raise IOError("Backup file exists already. Last time, Something went wrong ")

        try:
            # backup the db and open
            copyfile(self.db_path, self.db_backup_path)
            file = open(self.db_path)
        except IOError:
            # If db does not exist, create the file and populate with an empty dict
            file = open(self.db_path, 'w+')
            file.write(" {}")
            file.close()

            # backup the db and open
            copyfile(self.db_path, self.db_backup_path)
            file = open(self.db_path)

        self.from_json_string(file.read())

    def close(self):
        file = open(self.db_path, 'w')
        file.write(self.to_json_string())
        os.remove(self.db_backup_path)
