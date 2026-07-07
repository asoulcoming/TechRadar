"""Feishu (Lark) Bot integration via Webhook."""

import hashlib
import hmac
import base64
import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class FeishuNotifier:
    """Feishu custom bot for sending messages to group chats.

    Setup:
        1. In Feishu group → Settings → Bots → Add Custom Bot
        2. Copy the Webhook URL
        3. Optionally configure a signing secret for security
    """

    def __init__(self, webhook_url: str = "", secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret
        self.client = httpx.AsyncClient(timeout=15.0)
        self.enabled = bool(webhook_url)

    def _sign(self, timestamp: int) -> str:
        """Generate HMAC-SHA256 signature for Feishu webhook security."""
        if not self.secret:
            return ""
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    async def send_markdown(self, title: str, content: str) -> bool:
        """Send a rich-text Markdown message to Feishu.

        Args:
            title: Message title shown in push notification
            content: Markdown-formatted content body

        Returns: True if sent successfully.
        """
        if not self.enabled:
            logger.info("Feishu notifier disabled — no webhook URL configured.")
            return False

        timestamp = int(datetime.now().timestamp())
        sign = self._sign(timestamp)

        payload = {
            "timestamp": str(timestamp),
            "sign": sign,
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content,
                    }
                ],
            },
        }

        try:
            resp = await self.client.post(self.webhook_url, json=payload)
            resp_data = resp.json()
            if resp_data.get("code") == 0:
                logger.info("Feishu message sent successfully")
                return True
            else:
                logger.error(f"Feishu send failed: {resp_data}")
                return False
        except Exception as e:
            logger.error(f"Feishu send error: {e}")
            return False

    async def send_text(self, text: str, at_all: bool = False) -> bool:
        """Send a plain text message to Feishu.

        Args:
            text: Message text content
            at_all: Whether to @everyone in the group

        Returns: True if sent successfully.
        """
        if not self.enabled:
            return False

        timestamp = int(datetime.now().timestamp())
        sign = self._sign(timestamp)

        # Serialize at_all into the content string
        content_text = text
        if at_all:
            content_text = text + "\n\n<at user_id=\"all\">所有人</at>"

        content_payload = {
            "text": content_text,
        }

        payload = {
            "timestamp": str(timestamp),
            "sign": sign,
            "msg_type": "text",
            "content": content_payload,
        }

        try:
            resp = await self.client.post(self.webhook_url, json=payload)
            resp_data = resp.json()
            if resp_data.get("code") == 0:
                logger.info("Feishu text message sent successfully")
                return True
            else:
                logger.error(f"Feishu text send failed: {resp_data}")
                return False
        except Exception as e:
            logger.error(f"Feishu text send error: {e}")
            return False

    async def send_breaking_alert(self, topic: str, platform: str,
                                   change_percent: float, current_score: float) -> bool:
        """Send a breaking hotness alert.

        Args:
            topic: The trending topic name
            platform: Platform where the trend was detected
            change_percent: Percentage change in hotness
            current_score: Current hotness score

        Returns: True if sent successfully.
        """
        direction = "📈 飙升" if change_percent > 0 else "📉 骤降"
        text = (
            f"🚨 热点异动告警\n\n"
            f"主题: **{topic}**\n"
            f"平台: {platform}\n"
            f"变化: {direction} {change_percent:+.1f}%\n"
            f"当前热度: {current_score:.1f} 分\n\n"
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        return await self.send_text(text, at_all=True)

    async def close(self):
        await self.client.aclose()
