"""Typed probe outcomes for the project PostgreSQL image suite."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """One named probe outcome."""

    name: str
    ok: bool
    detail: str


@dataclass
class ProbeReport:
    """Aggregated disposable-run evidence."""

    results: list[ProbeResult] = field(default_factory=list)
    age_compatible: bool = False
    image_ref: str = ""

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.results.append(ProbeResult(name=name, ok=ok, detail=detail))

    @property
    def summary(self) -> dict[str, str]:
        return {item.name: ("pass" if item.ok else f"fail: {item.detail}") for item in self.results}

    @property
    def all_core_passed(self) -> bool:
        core = {
            "licenses",
            "versions",
            "sql",
            "bm25_vector",
            "transaction",
            "restart",
            "dump_restore",
        }
        return all(item.ok for item in self.results if item.name in core)
