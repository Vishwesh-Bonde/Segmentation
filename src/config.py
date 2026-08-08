from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    project_dir: Path
    input_dir: Path
    output_dir: Path
    logs_dir: Path
    encoding: str = "utf-8"

    @classmethod
    def from_project_root(cls, project_root: str | Path) -> "Config":
        root = Path(project_root)
        return cls(
            project_dir=root,
            input_dir=root / "input",
            output_dir=root / "output",
            logs_dir=root / "logs",
        )


DEFAULT_CONFIG = Config.from_project_root(Path(__file__).resolve().parent.parent)
