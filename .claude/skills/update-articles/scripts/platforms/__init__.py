"""Platform registry with auto-discovery for article metrics fetching."""

import importlib
import os
import pkgutil
import re
from abc import ABC, abstractmethod


class BasePlatform(ABC):
    """Abstract base class for platform-specific article metrics fetchers."""

    name: str = "Unknown"
    url_pattern: str = ""

    def can_handle(self, url: str) -> bool:
        return bool(re.search(self.url_pattern, url))

    def extract_post_id(self, url: str) -> str | None:
        match = re.search(self.url_pattern, url)
        return match.group(1) if match else None

    @abstractmethod
    def fetch_metrics(self, url: str) -> dict:
        """Fetch metrics for a given URL.

        Returns dict with keys: title, likes, comments, views, error
        Any value can be None if unavailable.
        """
        ...

    def cleanup(self):
        """Optional teardown (e.g., close browser instances)."""
        pass


class PlatformRegistry:
    """Registry that auto-discovers and manages platform fetchers."""

    def __init__(self):
        self._platforms: list[BasePlatform] = []

    def register(self, platform: BasePlatform):
        self._platforms.append(platform)

    def get_platform(self, url: str) -> BasePlatform | None:
        for platform in self._platforms:
            if platform.can_handle(url):
                return platform
        return None

    def cleanup_all(self):
        for platform in self._platforms:
            platform.cleanup()

    @property
    def platforms(self) -> list[BasePlatform]:
        return list(self._platforms)


def discover_platforms() -> PlatformRegistry:
    """Auto-discover and register all platform modules in this directory."""
    registry = PlatformRegistry()
    package_dir = os.path.dirname(__file__)

    for _importer, modname, _ispkg in pkgutil.iter_modules([package_dir]):
        if modname.startswith("_"):
            continue
        try:
            module = importlib.import_module(f".{modname}", package=__name__)
        except ImportError as e:
            print(f"[WARN] Failed to import platform module '{modname}': {e}")
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BasePlatform)
                and attr is not BasePlatform
            ):
                registry.register(attr())

    return registry
