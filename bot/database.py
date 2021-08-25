import os
import jsonpickle
from shutil import copyfile

from raid import *

def init_db(db_path: str, db_backup_path: str) -> RaidDict:
    if os.path.isfile(db_backup_path):
        raise IOError("Backup file exists already. Last time, Something went wrong ")

    try:
        # backup the db and open
        copyfile(db_path, db_backup_path)
        file = open(db_path)
    except IOError:
        # If db not exists, create the file and populate with an empty dict
        file = open(db_path, 'w+')
        file.write(" {}")
        file.close()

        # backup the db and open
        copyfile(db_path, db_backup_path)
        file = open(db_path)

    raids: RaidDict = jsonpickle.decode(file.read())
    return raids


def close_db(raids: RaidDict, db_path: str, db_backup_path: str):
    file = open(db_path, 'w')
    file.write(jsonpickle.encode(raids))

    os.remove(db_backup_path)