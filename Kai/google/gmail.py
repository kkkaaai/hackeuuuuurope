"""Gmail integration blocks."""

from __future__ import annotations

import logging
from typing import Any

from app.blocks.executor import register_implementation
from app.blocks.implementations.google.client import build_gmail_raw_message, get_gmail_service

logger = logging.getLogger("agentflow.blocks.google.gmail")


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


@register_implementation("google_gmail_list_messages")
async def gmail_list_messages(inputs: dict[str, Any]) -> dict[str, Any]:
    """List Gmail messages by query/label filters."""
    try:
        service = get_gmail_service()
        params = _clean_params({
            "q": inputs.get("query"),
            "labelIds": inputs.get("label_ids"),
            "maxResults": inputs.get("max_results"),
            "pageToken": inputs.get("page_token"),
            "includeSpamTrash": inputs.get("include_spam_trash"),
        })
        response = service.users().messages().list(userId="me", **params).execute()
    except Exception as e:
        logger.error("Gmail list messages error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail list messages failed: {type(e).__name__}") from None

    return {
        "messages": response.get("messages", []),
        "next_page_token": response.get("nextPageToken", ""),
        "result_size_estimate": response.get("resultSizeEstimate", 0),
    }


@register_implementation("google_gmail_get_message")
async def gmail_get_message(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch a Gmail message by ID."""
    message_id = inputs["message_id"]
    try:
        service = get_gmail_service()
        params = _clean_params({
            "format": inputs.get("format"),
            "metadataHeaders": inputs.get("metadata_headers"),
        })
        message = service.users().messages().get(userId="me", id=message_id, **params).execute()
    except Exception as e:
        logger.error("Gmail get message error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail get message failed: {type(e).__name__}") from None

    return {"message": message}


@register_implementation("google_gmail_send_message")
async def gmail_send_message(inputs: dict[str, Any]) -> dict[str, Any]:
    """Send a Gmail message."""
    try:
        service = get_gmail_service()
        raw_message = build_gmail_raw_message(inputs)
        body: dict[str, Any] = {"raw": raw_message}
        thread_id = inputs.get("thread_id")
        if thread_id:
            body["threadId"] = thread_id
        response = service.users().messages().send(userId="me", body=body).execute()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Gmail send message error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail send message failed: {type(e).__name__}") from None

    return {
        "message_id": response.get("id", ""),
        "thread_id": response.get("threadId", ""),
        "label_ids": response.get("labelIds", []),
    }


@register_implementation("google_gmail_modify_message_labels")
async def gmail_modify_message_labels(inputs: dict[str, Any]) -> dict[str, Any]:
    """Add or remove labels on a Gmail message."""
    message_id = inputs["message_id"]
    add_label_ids = inputs.get("add_label_ids") or []
    remove_label_ids = inputs.get("remove_label_ids") or []
    try:
        service = get_gmail_service()
        body = {"addLabelIds": add_label_ids, "removeLabelIds": remove_label_ids}
        message = service.users().messages().modify(userId="me", id=message_id, body=body).execute()
    except Exception as e:
        logger.error("Gmail modify message labels error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail modify message labels failed: {type(e).__name__}") from None

    return {"message": message}


@register_implementation("google_gmail_trash_message")
async def gmail_trash_message(inputs: dict[str, Any]) -> dict[str, Any]:
    """Trash a Gmail message."""
    message_id = inputs["message_id"]
    try:
        service = get_gmail_service()
        message = service.users().messages().trash(userId="me", id=message_id).execute()
    except Exception as e:
        logger.error("Gmail trash message error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail trash message failed: {type(e).__name__}") from None

    return {"message": message}


@register_implementation("google_gmail_untrash_message")
async def gmail_untrash_message(inputs: dict[str, Any]) -> dict[str, Any]:
    """Untrash a Gmail message."""
    message_id = inputs["message_id"]
    try:
        service = get_gmail_service()
        message = service.users().messages().untrash(userId="me", id=message_id).execute()
    except Exception as e:
        logger.error("Gmail untrash message error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail untrash message failed: {type(e).__name__}") from None

    return {"message": message}


@register_implementation("google_gmail_delete_message")
async def gmail_delete_message(inputs: dict[str, Any]) -> dict[str, Any]:
    """Permanently delete a Gmail message."""
    message_id = inputs["message_id"]
    try:
        service = get_gmail_service()
        service.users().messages().delete(userId="me", id=message_id).execute()
    except Exception as e:
        logger.error("Gmail delete message error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail delete message failed: {type(e).__name__}") from None

    return {"deleted": True}


@register_implementation("google_gmail_get_attachment")
async def gmail_get_attachment(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch a Gmail attachment."""
    message_id = inputs["message_id"]
    attachment_id = inputs["attachment_id"]
    try:
        service = get_gmail_service()
        attachment = (
            service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )
    except Exception as e:
        logger.error("Gmail get attachment error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail get attachment failed: {type(e).__name__}") from None

    return {"attachment_data": attachment.get("data", "")}


@register_implementation("google_gmail_list_drafts")
async def gmail_list_drafts(inputs: dict[str, Any]) -> dict[str, Any]:
    """List Gmail drafts."""
    try:
        service = get_gmail_service()
        params = _clean_params({
            "maxResults": inputs.get("max_results"),
            "pageToken": inputs.get("page_token"),
        })
        response = service.users().drafts().list(userId="me", **params).execute()
    except Exception as e:
        logger.error("Gmail list drafts error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail list drafts failed: {type(e).__name__}") from None

    return {
        "drafts": response.get("drafts", []),
        "next_page_token": response.get("nextPageToken", ""),
        "result_size_estimate": response.get("resultSizeEstimate", 0),
    }


@register_implementation("google_gmail_get_draft")
async def gmail_get_draft(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch a Gmail draft by ID."""
    draft_id = inputs["draft_id"]
    try:
        service = get_gmail_service()
        draft = service.users().drafts().get(userId="me", id=draft_id).execute()
    except Exception as e:
        logger.error("Gmail get draft error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail get draft failed: {type(e).__name__}") from None

    return {"draft": draft}


@register_implementation("google_gmail_create_draft")
async def gmail_create_draft(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a Gmail draft."""
    try:
        service = get_gmail_service()
        raw_message = build_gmail_raw_message(inputs)
        message: dict[str, Any] = {"raw": raw_message}
        thread_id = inputs.get("thread_id")
        if thread_id:
            message["threadId"] = thread_id
        response = service.users().drafts().create(
            userId="me", body={"message": message}
        ).execute()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Gmail create draft error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail create draft failed: {type(e).__name__}") from None

    message_data = response.get("message", {})
    return {
        "draft_id": response.get("id", ""),
        "message_id": message_data.get("id", ""),
        "thread_id": message_data.get("threadId", ""),
    }


@register_implementation("google_gmail_update_draft")
async def gmail_update_draft(inputs: dict[str, Any]) -> dict[str, Any]:
    """Update a Gmail draft."""
    draft_id = inputs["draft_id"]
    try:
        service = get_gmail_service()
        raw_message = build_gmail_raw_message(inputs)
        message: dict[str, Any] = {"raw": raw_message}
        thread_id = inputs.get("thread_id")
        if thread_id:
            message["threadId"] = thread_id
        response = service.users().drafts().update(
            userId="me", id=draft_id, body={"message": message}
        ).execute()
    except ValueError:
        raise
    except Exception as e:
        logger.error("Gmail update draft error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail update draft failed: {type(e).__name__}") from None

    message_data = response.get("message", {})
    return {
        "draft_id": response.get("id", ""),
        "message_id": message_data.get("id", ""),
        "thread_id": message_data.get("threadId", ""),
    }


@register_implementation("google_gmail_send_draft")
async def gmail_send_draft(inputs: dict[str, Any]) -> dict[str, Any]:
    """Send a Gmail draft."""
    draft_id = inputs["draft_id"]
    try:
        service = get_gmail_service()
        response = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
    except Exception as e:
        logger.error("Gmail send draft error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail send draft failed: {type(e).__name__}") from None

    return {
        "message_id": response.get("id", ""),
        "thread_id": response.get("threadId", ""),
    }


@register_implementation("google_gmail_delete_draft")
async def gmail_delete_draft(inputs: dict[str, Any]) -> dict[str, Any]:
    """Delete a Gmail draft."""
    draft_id = inputs["draft_id"]
    try:
        service = get_gmail_service()
        service.users().drafts().delete(userId="me", id=draft_id).execute()
    except Exception as e:
        logger.error("Gmail delete draft error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail delete draft failed: {type(e).__name__}") from None

    return {"deleted": True}


@register_implementation("google_gmail_list_labels")
async def gmail_list_labels(inputs: dict[str, Any]) -> dict[str, Any]:
    """List Gmail labels."""
    try:
        service = get_gmail_service()
        response = service.users().labels().list(userId="me").execute()
    except Exception as e:
        logger.error("Gmail list labels error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail list labels failed: {type(e).__name__}") from None

    return {"labels": response.get("labels", [])}


@register_implementation("google_gmail_get_label")
async def gmail_get_label(inputs: dict[str, Any]) -> dict[str, Any]:
    """Get a Gmail label."""
    label_id = inputs["label_id"]
    try:
        service = get_gmail_service()
        label = service.users().labels().get(userId="me", id=label_id).execute()
    except Exception as e:
        logger.error("Gmail get label error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail get label failed: {type(e).__name__}") from None

    return {"label": label}


@register_implementation("google_gmail_create_label")
async def gmail_create_label(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a Gmail label."""
    body = _clean_params({
        "name": inputs.get("name"),
        "messageListVisibility": inputs.get("message_list_visibility"),
        "labelListVisibility": inputs.get("label_list_visibility"),
    })
    try:
        service = get_gmail_service()
        label = service.users().labels().create(userId="me", body=body).execute()
    except Exception as e:
        logger.error("Gmail create label error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail create label failed: {type(e).__name__}") from None

    return {"label_id": label.get("id", ""), "name": label.get("name", "")}


@register_implementation("google_gmail_update_label")
async def gmail_update_label(inputs: dict[str, Any]) -> dict[str, Any]:
    """Update a Gmail label."""
    label_id = inputs["label_id"]
    body = _clean_params({
        "name": inputs.get("name"),
        "messageListVisibility": inputs.get("message_list_visibility"),
        "labelListVisibility": inputs.get("label_list_visibility"),
    })
    try:
        service = get_gmail_service()
        label = service.users().labels().update(userId="me", id=label_id, body=body).execute()
    except Exception as e:
        logger.error("Gmail update label error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail update label failed: {type(e).__name__}") from None

    return {"label_id": label.get("id", ""), "name": label.get("name", "")}


@register_implementation("google_gmail_delete_label")
async def gmail_delete_label(inputs: dict[str, Any]) -> dict[str, Any]:
    """Delete a Gmail label."""
    label_id = inputs["label_id"]
    try:
        service = get_gmail_service()
        service.users().labels().delete(userId="me", id=label_id).execute()
    except Exception as e:
        logger.error("Gmail delete label error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail delete label failed: {type(e).__name__}") from None

    return {"deleted": True}


@register_implementation("google_gmail_list_threads")
async def gmail_list_threads(inputs: dict[str, Any]) -> dict[str, Any]:
    """List Gmail threads by query/label filters."""
    try:
        service = get_gmail_service()
        params = _clean_params({
            "q": inputs.get("query"),
            "labelIds": inputs.get("label_ids"),
            "maxResults": inputs.get("max_results"),
            "pageToken": inputs.get("page_token"),
            "includeSpamTrash": inputs.get("include_spam_trash"),
        })
        response = service.users().threads().list(userId="me", **params).execute()
    except Exception as e:
        logger.error("Gmail list threads error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail list threads failed: {type(e).__name__}") from None

    return {
        "threads": response.get("threads", []),
        "next_page_token": response.get("nextPageToken", ""),
        "result_size_estimate": response.get("resultSizeEstimate", 0),
    }


@register_implementation("google_gmail_get_thread")
async def gmail_get_thread(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch a Gmail thread by ID."""
    thread_id = inputs["thread_id"]
    try:
        service = get_gmail_service()
        thread = service.users().threads().get(userId="me", id=thread_id).execute()
    except Exception as e:
        logger.error("Gmail get thread error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail get thread failed: {type(e).__name__}") from None

    return {"thread": thread}


@register_implementation("google_gmail_modify_thread_labels")
async def gmail_modify_thread_labels(inputs: dict[str, Any]) -> dict[str, Any]:
    """Add or remove labels on a Gmail thread."""
    thread_id = inputs["thread_id"]
    add_label_ids = inputs.get("add_label_ids") or []
    remove_label_ids = inputs.get("remove_label_ids") or []
    try:
        service = get_gmail_service()
        body = {"addLabelIds": add_label_ids, "removeLabelIds": remove_label_ids}
        thread = service.users().threads().modify(userId="me", id=thread_id, body=body).execute()
    except Exception as e:
        logger.error("Gmail modify thread labels error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail modify thread labels failed: {type(e).__name__}") from None

    return {"thread": thread}


@register_implementation("google_gmail_trash_thread")
async def gmail_trash_thread(inputs: dict[str, Any]) -> dict[str, Any]:
    """Trash a Gmail thread."""
    thread_id = inputs["thread_id"]
    try:
        service = get_gmail_service()
        thread = service.users().threads().trash(userId="me", id=thread_id).execute()
    except Exception as e:
        logger.error("Gmail trash thread error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail trash thread failed: {type(e).__name__}") from None

    return {"thread": thread}


@register_implementation("google_gmail_untrash_thread")
async def gmail_untrash_thread(inputs: dict[str, Any]) -> dict[str, Any]:
    """Untrash a Gmail thread."""
    thread_id = inputs["thread_id"]
    try:
        service = get_gmail_service()
        thread = service.users().threads().untrash(userId="me", id=thread_id).execute()
    except Exception as e:
        logger.error("Gmail untrash thread error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail untrash thread failed: {type(e).__name__}") from None

    return {"thread": thread}


@register_implementation("google_gmail_delete_thread")
async def gmail_delete_thread(inputs: dict[str, Any]) -> dict[str, Any]:
    """Permanently delete a Gmail thread."""
    thread_id = inputs["thread_id"]
    try:
        service = get_gmail_service()
        service.users().threads().delete(userId="me", id=thread_id).execute()
    except Exception as e:
        logger.error("Gmail delete thread error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail delete thread failed: {type(e).__name__}") from None

    return {"deleted": True}


@register_implementation("google_gmail_list_history")
async def gmail_list_history(inputs: dict[str, Any]) -> dict[str, Any]:
    """List Gmail history records."""
    start_history_id = inputs["start_history_id"]
    label_id = inputs.get("label_id")
    try:
        service = get_gmail_service()
        params = _clean_params({
            "startHistoryId": start_history_id,
            "labelId": label_id,
            "historyTypes": inputs.get("history_types"),
            "pageToken": inputs.get("page_token"),
            "maxResults": inputs.get("max_results"),
        })
        response = service.users().history().list(userId="me", **params).execute()
    except Exception as e:
        logger.error("Gmail list history error [%s]: %s", type(e).__name__, e)
        raise ValueError(f"Gmail list history failed: {type(e).__name__}") from None

    return {
        "history": response.get("history", []),
        "history_id": response.get("historyId", ""),
        "next_page_token": response.get("nextPageToken", ""),
    }
