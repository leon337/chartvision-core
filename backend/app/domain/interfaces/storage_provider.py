from typing import Protocol


class StorageProvider(Protocol):
    def healthcheck(self) -> bool: ...
