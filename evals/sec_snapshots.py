"""Combine pinned public SEC snapshots for offline evaluation only."""

import hashlib

from agents.edgar import EdgarClient


class SnapshotClient(EdgarClient):
    def __init__(self):
        super().__init__('tests/fixtures/edgar', offline=True)
        self.snapshots = [EdgarClient(path, offline=True) for path in
                          ('tests/fixtures/edgar', 'tests/fixtures/edgar_validation')]

    def get(self, url: str) -> dict:
        name = hashlib.sha256(url.encode()).hexdigest() + '.json'
        for snapshot in self.snapshots:
            if (snapshot.cache_dir / name).exists():
                return snapshot.get(url)
        return super().get(url)

    def tickers(self) -> dict:
        entries = {}
        for snapshot in self.snapshots:
            if snapshot.cache_dir.exists():
                for entry in snapshot.tickers().values():
                    entries[entry['ticker']] = entry
        return {str(i): e for i, e in enumerate(entries.values())}
