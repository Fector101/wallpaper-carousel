from abc import ABC, abstractmethod


MOCK_CATEGORIES = [
    "All",
    "Nature",
    "Abstract",
    "Minimal",
    "Dark",
    "Colorful",
]

MOCK_WALLPAPERS = [
    {
        "id": "wp001",
        "name": "Mountain Sunrise",
        "category": "Nature",
        "author": "Alex Rivers",
        "thumbnail_url": "https://picsum.photos/seed/mountain_sun/400/400",
        "image_url": "https://picsum.photos/seed/mountain_sun/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 2400,
    },
    {
        "id": "wp002",
        "name": "Ocean Waves",
        "category": "Nature",
        "author": "Marina Cole",
        "thumbnail_url": "https://picsum.photos/seed/ocean_waves/400/400",
        "image_url": "https://picsum.photos/seed/ocean_waves/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 3100,
    },
    {
        "id": "wp003",
        "name": "Neon Flow",
        "category": "Abstract",
        "author": "Pixel Artist",
        "thumbnail_url": "https://picsum.photos/seed/neon_flow/400/400",
        "image_url": "https://picsum.photos/seed/neon_flow/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 1800,
    },
    {
        "id": "wp004",
        "name": "Geometric Shapes",
        "category": "Abstract",
        "author": "Design Lab",
        "thumbnail_url": "https://picsum.photos/seed/geometric/400/400",
        "image_url": "https://picsum.photos/seed/geometric/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 1200,
    },
    {
        "id": "wp005",
        "name": "Pure White",
        "category": "Minimal",
        "author": "Clean Studio",
        "thumbnail_url": "https://picsum.photos/seed/pure_white/400/400",
        "image_url": "https://picsum.photos/seed/pure_white/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 400,
    },
    {
        "id": "wp006",
        "name": "Simple Lines",
        "category": "Minimal",
        "author": "Minimal Co",
        "thumbnail_url": "https://picsum.photos/seed/simple_lines/400/400",
        "image_url": "https://picsum.photos/seed/simple_lines/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 600,
    },
    {
        "id": "wp007",
        "name": "Midnight City",
        "category": "Dark",
        "author": "Night Owl",
        "thumbnail_url": "https://picsum.photos/seed/midnight/400/400",
        "image_url": "https://picsum.photos/seed/midnight/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 2800,
    },
    {
        "id": "wp008",
        "name": "Shadow Play",
        "category": "Dark",
        "author": "Dark Art",
        "thumbnail_url": "https://picsum.photos/seed/shadow/400/400",
        "image_url": "https://picsum.photos/seed/shadow/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 1900,
    },
    {
        "id": "wp009",
        "name": "Rainbow Gradient",
        "category": "Colorful",
        "author": "Vivid Works",
        "thumbnail_url": "https://picsum.photos/seed/rainbow/400/400",
        "image_url": "https://picsum.photos/seed/rainbow/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 1500,
    },
    {
        "id": "wp010",
        "name": "Autumn Forest",
        "category": "Nature",
        "author": "Leaf Studio",
        "thumbnail_url": "https://picsum.photos/seed/autumn/400/400",
        "image_url": "https://picsum.photos/seed/autumn/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 3400,
    },
    {
        "id": "wp011",
        "name": "Liquid Chrome",
        "category": "Abstract",
        "author": "Metal Works",
        "thumbnail_url": "https://picsum.photos/seed/chrome/400/400",
        "image_url": "https://picsum.photos/seed/chrome/1920/1080",
        "resolution": "1920/1080",
        "size_kb": 2100,
    },
    {
        "id": "wp012",
        "name": "Soft Pastel",
        "category": "Colorful",
        "author": "Pastel Dreams",
        "thumbnail_url": "https://picsum.photos/seed/pastel/400/400",
        "image_url": "https://picsum.photos/seed/pastel/1920/1080",
        "resolution": "1920x1080",
        "size_kb": 1100,
    },
]


class MarketplaceProvider(ABC):
    @abstractmethod
    def get_categories(self) -> list[str]:
        ...

    @abstractmethod
    def get_wallpapers(self, category: str = "All") -> list[dict]:
        ...

    @abstractmethod
    def get_wallpaper_by_id(self, wallpaper_id: str) -> dict | None:
        ...


class MockMarketplaceProvider(MarketplaceProvider):
    def get_categories(self) -> list[str]:
        return MOCK_CATEGORIES

    def get_wallpapers(self, category: str = "All") -> list[dict]:
        if category == "All":
            return MOCK_WALLPAPERS
        return [w for w in MOCK_WALLPAPERS if w["category"] == category]

    def get_wallpaper_by_id(self, wallpaper_id: str) -> dict | None:
        for w in MOCK_WALLPAPERS:
            if w["id"] == wallpaper_id:
                return w
        return None


def get_marketplace_provider() -> MarketplaceProvider:
    return MockMarketplaceProvider()
