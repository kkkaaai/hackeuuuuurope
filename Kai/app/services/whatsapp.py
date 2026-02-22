"""WhatsApp Cloud API helpers."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.config import settings

log = logging.getLogger(__name__)


@dataclass
class IncomingMessage:
    wa_id: str
    phone_number_id: str
    text: str | None
    message_id: str | None
    timestamp: str | None
    contact_name: str | None


def parse_incoming_messages(payload: dict) -> list[IncomingMessage]:
    messages: list[IncomingMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")
            contacts = value.get("contacts", [])
            contact_name = None
            if contacts:
                profile = contacts[0].get("profile", {})
                contact_name = profile.get("name")
            for msg in value.get("messages", []):
                wa_id = msg.get("from")
                if not wa_id:
                    continue
                msg_type = msg.get("type")
                text = None
                if msg_type == "text":
                    text = msg.get("text", {}).get("body")
                messages.append(
                    IncomingMessage(
                        wa_id=wa_id,
                        phone_number_id=phone_number_id or settings.whatsapp_phone_number_id,
                        text=text,
                        message_id=msg.get("id"),
                        timestamp=msg.get("timestamp"),
                        contact_name=contact_name,
                    )
                )
    return messages


class WhatsAppClient:
    def __init__(self) -> None:
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.api_version = settings.whatsapp_api_version

    def _post_json(self, path: str, payload: dict, *, access_token: str | None = None) -> dict:
        token = access_token or self.access_token
        url = f"https://graph.facebook.com/{self.api_version}/{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8") if exc.fp else ""
            log.error("WhatsApp API error %s: %s", exc.code, err_body)
            raise

    def send_text(
        self,
        wa_id: str,
        text: str,
        *,
        phone_number_id: str | None = None,
        access_token: str | None = None,
    ) -> None:
        token = access_token or self.access_token
        sender_phone_number_id = phone_number_id or self.phone_number_id
        if not token or not sender_phone_number_id:
            log.warning("WhatsApp credentials missing; skipping send")
            return
        payload = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "text",
            "text": {"body": text},
        }
        self._post_json(f"{sender_phone_number_id}/messages", payload, access_token=token)

    def send_media(
        self,
        wa_id: str,
        media_url: str,
        mime_type: str | None,
        filename: str | None,
        caption: str | None,
        *,
        phone_number_id: str | None = None,
        access_token: str | None = None,
    ) -> None:
        token = access_token or self.access_token
        sender_phone_number_id = phone_number_id or self.phone_number_id
        if not token or not sender_phone_number_id:
            log.warning("WhatsApp credentials missing; skipping send")
            return
        media_type = _media_type_from_mime(mime_type, filename)
        media_payload: dict[str, Any] = {"link": media_url}
        if filename and media_type == "document":
            media_payload["filename"] = filename
        if caption and media_type in {"image", "video", "document"}:
            media_payload["caption"] = caption
        payload = {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": media_type,
            media_type: media_payload,
        }
        self._post_json(f"{sender_phone_number_id}/messages", payload, access_token=token)

    def send_result(
        self,
        wa_id: str,
        output: dict,
        *,
        phone_number_id: str | None = None,
        access_token: str | None = None,
    ) -> None:
        if not output:
            self.send_text(
                wa_id,
                "No output produced by the pipeline.",
                phone_number_id=phone_number_id,
                access_token=access_token,
            )
            return

        if "whatsapp" in output:
            self._send_custom_payload(
                wa_id,
                output["whatsapp"],
                phone_number_id=phone_number_id,
                access_token=access_token,
            )
            return

        if "card" in output:
            text = _render_card(output["card"])
            self.send_text(wa_id, text, phone_number_id=phone_number_id, access_token=access_token)
            return

        if "summary" in output:
            self.send_text(
                wa_id,
                str(output.get("summary")),
                phone_number_id=phone_number_id,
                access_token=access_token,
            )
            return

        if "result" in output:
            self.send_text(
                wa_id,
                str(output.get("result")),
                phone_number_id=phone_number_id,
                access_token=access_token,
            )
            return

        self.send_text(
            wa_id,
            json.dumps(output)[:3000],
            phone_number_id=phone_number_id,
            access_token=access_token,
        )

    def _send_custom_payload(
        self,
        wa_id: str,
        payload: dict,
        *,
        phone_number_id: str | None = None,
        access_token: str | None = None,
    ) -> None:
        text = payload.get("text")
        media_url = payload.get("media_url") or payload.get("file_url")
        mime_type = payload.get("mime_type")
        filename = payload.get("filename")

        if media_url:
            self.send_media(
                wa_id,
                media_url,
                mime_type,
                filename,
                text,
                phone_number_id=phone_number_id,
                access_token=access_token,
            )
            return
        if text:
            self.send_text(wa_id, text, phone_number_id=phone_number_id, access_token=access_token)


def _media_type_from_mime(mime_type: str | None, filename: str | None) -> str:
    if mime_type:
        if mime_type.startswith("image/"):
            return "image"
        if mime_type.startswith("video/"):
            return "video"
        if mime_type.startswith("audio/"):
            return "audio"
        return "document"
    if filename:
        lower = filename.lower()
        if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            return "image"
        if lower.endswith((".mp4", ".mov", ".avi")):
            return "video"
        if lower.endswith((".mp3", ".wav", ".m4a")):
            return "audio"
    return "document"


def _render_card(card: dict) -> str:
    lines = []
    title = card.get("title")
    highlight = card.get("highlight")
    if title:
        lines.append(str(title))
    if highlight:
        lines.append(str(highlight))
    fields = card.get("fields") or []
    for field in fields:
        label = field.get("label")
        value = field.get("value")
        if label and value is not None:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)
