from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredFile:
    path: Path
    public_url: str
