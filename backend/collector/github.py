"""GitHub Trending data source."""

import json
import logging
from datetime import datetime

import httpx

from collector.base import DataSource, RawPost

logger = logging.getLogger(__name__)

GITHUB_TRENDING_API = "https://api.github.com/search/repositories"


class GitHubSource(DataSource):
    platform = "github"

    def __init__(self, token: str = ""):
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-hotspot-agent/1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = httpx.AsyncClient(headers=headers, timeout=30.0)
        self.token = token

    async def search(self, keyword: str, limit: int = 50) -> list[RawPost]:
        """Search GitHub repositories by keyword."""
        posts = []

        # Search repos sorted by stars
        resp = await self.client.get(
            GITHUB_TRENDING_API,
            params={
                "q": f"{keyword} in:name,description,topics",
                "sort": "stars",
                "order": "desc",
                "per_page": min(limit, 100),
            },
        )

        if resp.status_code != 200:
            logger.warning(f"GitHub API returned {resp.status_code}: {resp.text[:200]}")
            return posts

        data = resp.json()
        for item in data.get("items", [])[:limit]:
            posts.append(RawPost(
                platform="github",
                post_id=f"github-{item['id']}",
                keyword=keyword,
                title=item.get("full_name", ""),
                url=item.get("html_url", ""),
                author=item.get("owner", {}).get("login", ""),
                publish_time=datetime.fromisoformat(
                    item.get("updated_at", "").replace("Z", "+00:00")
                ),
                star_count=item.get("stargazers_count", 0),
                view_count=item.get("watchers_count", 0),
                like_count=item.get("stargazers_count", 0),
                comment_count=item.get("open_issues_count", 0),
                share_count=item.get("forks_count", 0),
                content_summary=item.get("description", "") or "",
                tags=item.get("topics", []),
                raw_data=item,
            ))
        return posts

    async def fetch_trending(self, topic: str = "", limit: int = 50) -> list[RawPost]:
        """Fetch trending repos. If topic specified, search for it; otherwise fetch by stars."""
        keyword = topic if topic else "stars:>100"
        return await self.search(keyword, limit=limit)

    async def fetch_by_language(self, language: str, limit: int = 20) -> list[RawPost]:
        """Fetch top repos for a specific language."""
        return await self.search(f"language:{language} stars:>10", limit=limit)

    async def health_check(self) -> bool:
        try:
            resp = await self.client.get(GITHUB_TRENDING_API, params={"q": "test", "per_page": 1})
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()
