from jsonpickle import encode, decode
from abc import ABC, abstractmethod
from raid import RaidDict, Raid


class Database(ABC):
    """
    This class is an interface to allow multiple storage solutions in the future.
    To realize the interace, the abstract methods `__init__(self)` and `close(self)`
    have to be implemented.
    """

    raid_db: RaidDict = {}

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def close(self):
        pass

    def __del__(self):
        self.close()

    def from_json_string(self, json: str):
        self.raid_db = decode(json)

    def to_json_string(self) -> str:
        return encode(self.raid_db)

    def store(self, raid: Raid):
        self.raid_db[raid.name] = raid

    def find_raid(self, raid_name: str) -> Raid:
        raid_name = raid_name.strip()
        return self.raid_db.get(raid_name)
