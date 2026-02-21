"""Email send block — sends email via Resend, or logs if API key is not configured."""

import os
import re
import uuid


def _sanitize(value: str) -> str:
    """Strip characters that could enable header injection."""
    return re.sub(r"[\r\n\t]", "", value)


def _validate_email(addr: str) -> str:
    """Basic single-address validation — rejects multi-recipient tricks."""
    addr = addr.strip()
    if not re.fullmatch(r"[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+", addr):
        raise ValueError(f"Invalid email address: {addr}")
    return addr


async def execute(inputs: dict, context: dict) -> dict:
    to = _validate_email(inputs["to"])
    subject = _sanitize(inputs["subject"])
    body = inputs["body"][:10_000]
    from_name = _sanitize(inputs.get("from_name", "AgentFlow"))

    api_key = os.environ.get("RESEND_API_KEY", "")

    if not api_key or api_key == "...":
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        print(f"[EMAIL STUB] To: {to} | Subject: {subject} | From: {from_name}")
        return {"message_id": msg_id, "status": "sent (stub)"}

    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"{from_name} <onboarding@resend.dev>",
                    "to": [to],
                    "subject": subject,
                    "text": body,
                },
            )
    except httpx.HTTPError as exc:
        return {"message_id": "", "status": f"failed (network: {exc})"}

    if response.status_code == 200:
        data = response.json()
        return {"message_id": data.get("id", ""), "status": "sent"}

    return {
        "message_id": "",
        "status": f"failed ({response.status_code})",
    }
