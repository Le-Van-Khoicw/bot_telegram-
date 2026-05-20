import os
import re
from datetime import datetime, timedelta
from html import unescape
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests


GRAPH_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_MESSAGES_URL = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"

DEFAULT_GRAPH_SCOPE = "https://graph.microsoft.com/Mail.Read offline_access"
DISPLAY_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class MailReaderError(RuntimeError):
    pass


def parse_mail_account(raw: str) -> Dict[str, str]:
    """
    Supports common shop formats:
    - email|refresh_token|client_id
    - email|password|refresh_token|client_id
    - email----refresh_token----client_id

    If client_id is missing, MS_GRAPH_CLIENT_ID / MAIL_GRAPH_CLIENT_ID is used.
    """
    text = (raw or "").strip()
    if not text:
        raise MailReaderError("Thiếu chuỗi mail.")

    sep = "|" if "|" in text else "----"
    parts = [re.sub(r"\s+", "", p.strip()) for p in text.split(sep) if p.strip()]
    if len(parts) < 2:
        raise MailReaderError("Sai định dạng. Cần dạng email|refresh_token|client_id.")

    email = parts[0]
    if "@" not in email:
        raise MailReaderError("Không nhận ra email ở đầu chuỗi.")

    client_id = os.getenv("MS_GRAPH_CLIENT_ID", "").strip() or os.getenv("MAIL_GRAPH_CLIENT_ID", "").strip()

    if len(parts) >= 4:
        refresh_token = parts[-2]
        client_id = parts[-1]
    elif len(parts) == 3:
        refresh_token = parts[1]
        client_id = parts[2]
    else:
        refresh_token = parts[1]

    if not refresh_token:
        raise MailReaderError("Thiếu refresh_token.")
    if not client_id:
        raise MailReaderError("Thiếu client_id. Dùng email|refresh_token|client_id hoặc set MS_GRAPH_CLIENT_ID.")

    return {
        "email": email,
        "refresh_token": refresh_token,
        "client_id": client_id,
    }


def get_graph_access_token(refresh_token: str, client_id: str) -> str:
    data = {
        "client_id": client_id,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": DEFAULT_GRAPH_SCOPE,
    }
    try:
        resp = requests.post(GRAPH_TOKEN_URL, data=data, timeout=20)
    except requests.RequestException as e:
        raise MailReaderError(f"Lỗi kết nối Microsoft OAuth: {e}") from e

    if resp.status_code >= 400:
        detail = _short_error(resp)
        raise MailReaderError(f"Không lấy được access_token ({resp.status_code}): {detail}")

    token = resp.json().get("access_token")
    if not token:
        raise MailReaderError("Microsoft không trả access_token.")
    return token


def read_inbox_messages(raw_account: str, limit: int = 5) -> Dict[str, Any]:
    account = parse_mail_account(raw_account)
    token = get_graph_access_token(account["refresh_token"], account["client_id"])

    params = {
        "$top": max(1, min(int(limit or 5), 10)),
        "$orderby": "receivedDateTime desc",
        "$select": "subject,from,receivedDateTime,bodyPreview,body",
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(GRAPH_MESSAGES_URL, headers=headers, params=params, timeout=20)
    except requests.RequestException as e:
        raise MailReaderError(f"Lỗi kết nối Microsoft Graph: {e}") from e

    if resp.status_code >= 400:
        detail = _short_error(resp)
        raise MailReaderError(f"Không đọc được inbox ({resp.status_code}): {detail}")

    messages = [_normalize_message(m) for m in resp.json().get("value", [])]
    return {"email": account["email"], "messages": messages}


def check_gpt_plus_mail(raw_account: str, limit: int = 30, active_days: int = 45) -> Dict[str, Any]:
    """
    Check Microsoft inbox for OpenAI/ChatGPT Plus subscription receipts.
    This does not log in to ChatGPT; it only searches the mailbox that the
    account line authorizes via refresh token.
    """
    account = parse_mail_account(raw_account)
    token = get_graph_access_token(account["refresh_token"], account["client_id"])
    max_messages = max(1, min(int(limit or 30), 50))

    params = {
        "$top": max_messages,
        "$orderby": "receivedDateTime desc",
        "$select": "subject,from,receivedDateTime,bodyPreview,body",
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(GRAPH_MESSAGES_URL, headers=headers, params=params, timeout=25)
    except requests.RequestException as e:
        raise MailReaderError(f"Lỗi kết nối Microsoft Graph: {e}") from e

    if resp.status_code >= 400:
        detail = _short_error(resp)
        raise MailReaderError(f"Không đọc được inbox ({resp.status_code}): {detail}")

    cutoff = datetime.now(DISPLAY_TZ) - timedelta(days=max(1, int(active_days or 45)))
    best_plus: Optional[Dict[str, Any]] = None
    best_old: Optional[Dict[str, Any]] = None

    for raw_msg in resp.json().get("value", []):
        normalized = _normalize_message(raw_msg)
        banned_score = _openai_banned_score(normalized)
        if banned_score > 0:
            return {
                "email": account["email"],
                "status": "BANNED",
                "label": "Acc die / bi ban",
                "matched": {
                    "from": normalized.get("from", ""),
                    "subject": normalized.get("subject", ""),
                    "time": normalized.get("time", ""),
                    "score": banned_score,
                    "preview": normalized.get("preview", "")[:240],
                },
            }

        score = _gpt_plus_score(normalized)
        if score <= 0:
            continue

        received_dt = _parse_graph_time(raw_msg.get("receivedDateTime") or "")
        hit = {
            "from": normalized.get("from", ""),
            "subject": normalized.get("subject", ""),
            "time": normalized.get("time", ""),
            "score": score,
            "preview": normalized.get("preview", "")[:240],
        }
        if received_dt and received_dt >= cutoff:
            if not best_plus:
                best_plus = hit
            continue
        if not best_old:
            best_old = hit

    if best_plus:
        return {
            "email": account["email"],
            "status": "PLUS",
            "label": "Có gói",
            "matched": best_plus,
        }

    if best_old:
        return {
            "email": account["email"],
            "status": "OLD_PLUS",
            "label": "Có mail Plus cũ",
            "matched": best_old,
        }

    return {
        "email": account["email"],
        "status": "NO_PLUS_MAIL",
        "label": "Không thấy mail Plus",
        "matched": None,
    }


def extract_codes(text: str) -> List[str]:
    found = re.findall(r"(?<!\d)(\d{4,8})(?!\d)", text or "")
    out: List[str] = []
    for code in found:
        if code not in out:
            out.append(code)
    return out[:5]


def _normalize_message(msg: Dict[str, Any]) -> Dict[str, str]:
    sender = (((msg.get("from") or {}).get("emailAddress") or {}).get("address") or "").strip()
    sender_name = (((msg.get("from") or {}).get("emailAddress") or {}).get("name") or "").strip()
    subject = (msg.get("subject") or "(no subject)").strip()
    preview = (msg.get("bodyPreview") or "").strip()
    body_text = _plain_body((((msg.get("body") or {}).get("content")) or "").strip())
    received = _format_time(msg.get("receivedDateTime") or "")
    codes = extract_codes(f"{subject}\n{preview}\n{body_text}")
    return {
        "from": sender or sender_name or "(unknown)",
        "time": received,
        "subject": subject,
        "preview": preview,
        "body": body_text,
        "codes": ", ".join(codes),
    }


def _gpt_plus_score(message: Dict[str, str]) -> int:
    sender = (message.get("from") or "").lower()
    text = " ".join([
        message.get("subject", ""),
        message.get("preview", ""),
        message.get("body", ""),
    ]).lower()

    score = 0
    if "openai" in sender or "openai" in text:
        score += 1
    strong_patterns = [
        "chatgpt plus subscription",
        "bạn đã đăng ký thành công chatgpt plus",
        "ban da dang ky thanh cong chatgpt plus",
        "you successfully subscribed to chatgpt plus",
        "your chatgpt plus subscription",
    ]
    medium_patterns = [
        "chatgpt plus",
        "quản lý đăng ký của bạn",
        "quan ly dang ky cua ban",
        "đơn hàng số: sub_",
        "don hang so: sub_",
        "order number: sub_",
        "subscription",
    ]
    for pattern in strong_patterns:
        if pattern in text:
            score += 5
    for pattern in medium_patterns:
        if pattern in text:
            score += 2
    return score if score >= 4 else 0


def _openai_banned_score(message: Dict[str, str]) -> int:
    sender = (message.get("from") or "").lower()
    text = " ".join([
        message.get("subject", ""),
        message.get("preview", ""),
        message.get("body", ""),
    ]).lower()

    if "openai" not in sender and "openai" not in text and "chatgpt" not in text:
        return 0

    score = 1
    strong_patterns = [
        "your account has been banned",
        "account has been banned",
        "your account was banned",
        "account was banned",
        "access deactivated",
        "account deactivated",
        "account has been deactivated",
        "account was deactivated",
        "access disabled",
        "account disabled",
        "account has been disabled",
        "account suspended",
        "account has been suspended",
        "can no longer be used",
        "violated our terms and usage policies",
        "violated our terms",
        "recent activity violated",
    ]
    medium_patterns = [
        "initiate appeal",
        "start an appeal",
        "appeal",
        "usage policies",
        "terms and usage policies",
    ]
    for pattern in strong_patterns:
        if pattern in text:
            score += 5
    for pattern in medium_patterns:
        if pattern in text:
            score += 2
    return score if score >= 6 else 0


def _parse_graph_time(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(DISPLAY_TZ)
    except Exception:
        return None


def _plain_body(value: str) -> str:
    if not value:
        return ""
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return " ".join(text.split())


def _format_time(value: str) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(DISPLAY_TZ).strftime("%H:%M %d/%m/%Y GMT+7")
    except Exception:
        return value


def _short_error(resp: requests.Response) -> str:
    try:
        data = resp.json()
        err = data.get("error") or {}
        if isinstance(err, dict):
            return (err.get("message") or err.get("code") or str(data))[:500]
        return str(data)[:500]
    except Exception:
        return resp.text[:500]
