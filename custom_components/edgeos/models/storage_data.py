from typing import Optional


class StorageData:
    key: Optional[str]

    def __init__(self):
        self.key = None

    @staticmethod
    def from_dict(obj: dict):
        data = StorageData()

        if obj is not None:
            data.key = obj.get("key")

        return data

    def to_dict(self):
        obj = {"key": self.key}

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
