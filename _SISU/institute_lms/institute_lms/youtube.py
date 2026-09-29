"""Per-teacher OAuth connection and live broadcast scheduling."""
import secrets
from urllib.parse import urlencode
from datetime import timezone
from zoneinfo import ZoneInfo
import requests
import frappe
from frappe.utils import get_url, get_datetime
from .api import identity, require_role, classroom_for, scoped


def config():
    client = frappe.conf.get("il_youtube_client_id")
    secret = frappe.conf.get("il_youtube_client_secret")
    if not client or not secret:
        frappe.throw("YouTube OAuth is not configured")
    return client, secret, get_url("/api/method/institute_lms.youtube.callback")


@frappe.whitelist(methods=["POST"])
def connect():
    inst, member = identity()
    require_role(member, "Teacher")
    client, _, redirect = config()
    state = secrets.token_urlsafe(32)
    frappe.cache.set_value(f"il_youtube_state:{state}", {"user": frappe.session.user, "member": member.name, "institute": inst.name}, expires_in_sec=600)
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({"client_id": client, "redirect_uri": redirect,
        "response_type": "code", "scope": "https://www.googleapis.com/auth/youtube.force-ssl",
        "access_type": "offline", "prompt": "consent", "state": state})


@frappe.whitelist(methods=["GET"])
def callback(state: str, code: str | None = None, error: str | None = None):
    context = frappe.cache.get_value(f"il_youtube_state:{state}")
    frappe.cache.delete_value(f"il_youtube_state:{state}")
    if not context or context["user"] != frappe.session.user:
        frappe.throw("OAuth session expired", frappe.PermissionError)
    if error or not code:
        frappe.throw("YouTube connection was not authorized")
    client, secret, redirect = config()
    response = requests.post("https://oauth2.googleapis.com/token", timeout=20, data={"code": code,
        "client_id": client, "client_secret": secret, "redirect_uri": redirect, "grant_type": "authorization_code"})
    if not response.ok or not response.json().get("refresh_token"):
        frappe.throw("YouTube authorization failed. Reconnect and grant offline access.")
    existing = frappe.db.get_value("IL YouTube Connection", {"member": context["member"]}, "name")
    doc = frappe.get_doc("IL YouTube Connection", existing) if existing else frappe.new_doc("IL YouTube Connection")
    doc.update({"institute": context["institute"], "member": context["member"], "refresh_token": response.json()["refresh_token"]})
    doc.save(ignore_permissions=True)
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/campus?youtube=connected"


def token(member):
    name = frappe.db.get_value("IL YouTube Connection", {"member": member}, "name")
    if not name:
        frappe.throw("The classroom teacher must connect YouTube first")
    connection = frappe.get_doc("IL YouTube Connection", name)
    client, secret, _ = config()
    response = requests.post("https://oauth2.googleapis.com/token", timeout=20, data={"client_id": client,
        "client_secret": secret, "refresh_token": connection.get_password("refresh_token"), "grant_type": "refresh_token"})
    if not response.ok:
        frappe.throw("Reconnect your YouTube account")
    return response.json()["access_token"]


@frappe.whitelist(methods=["POST"])
def schedule_broadcast(session: str, privacy: str = "unlisted", made_for_kids: bool | None = None):
    inst, _ = identity()
    doc = scoped("IL Session", session, inst)
    _, _, room = classroom_for(doc.classroom, write=True)
    if privacy not in ("public", "unlisted", "private") or doc.mode != "Online":
        frappe.throw("Select a valid privacy setting for an online session")
    if type(made_for_kids) is not bool:
        frappe.throw("Choose the broadcast audience in Live Studio before creating it")
    if doc.youtube_id:
        frappe.throw("This session already has a YouTube video")
    start = get_datetime(doc.starts_at).replace(tzinfo=ZoneInfo("Asia/Colombo")).astimezone(timezone.utc).isoformat()
    # Serialize same-session creation. If a network timeout occurs, reconcile in Studio before retrying.
    with frappe.cache.lock(f"il_broadcast:{doc.name}", timeout=40, blocking_timeout=1):
        if frappe.db.get_value("IL Session", doc.name, "youtube_id"):
            frappe.throw("This session already has a YouTube video")
        response = requests.post("https://www.googleapis.com/youtube/v3/liveBroadcasts", timeout=20,
            params={"part": "snippet,status,contentDetails"}, headers={"Authorization": f"Bearer {token(room.teacher)}"},
            json={"snippet": {"title": doc.title, "description": doc.description or "", "scheduledStartTime": start},
                  "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": made_for_kids},
                  "contentDetails": {"enableEmbed": True, "enableAutoStart": True, "enableAutoStop": True}})
        if not response.ok:
            frappe.throw(f"YouTube could not schedule the broadcast (HTTP {response.status_code}). Check channel live-stream eligibility.")
        doc.youtube_id = response.json()["id"]
        doc.youtube_privacy = privacy
        doc.save(ignore_permissions=True)
        from .notifications import classroom_event
        classroom_event(room, f"live:{doc.name}:{doc.youtube_id}", f"Live session ready: {doc.title}")
    return {"video_id": doc.youtube_id, "studio_url": "https://studio.youtube.com/", "watch_url": f"https://www.youtube.com/watch?v={doc.youtube_id}"}


@frappe.whitelist(methods=["POST"])
def sync_broadcast(session: str):
    inst, _ = identity()
    doc = scoped("IL Session", session, inst)
    _, _, room = classroom_for(doc.classroom, write=True)
    if not doc.youtube_id:
        frappe.throw("Schedule or attach a broadcast first")
    headers = {"Authorization": f"Bearer {token(room.teacher)}"}
    current = requests.get("https://www.googleapis.com/youtube/v3/liveBroadcasts", timeout=20,
        headers=headers, params={"part": "snippet", "id": doc.youtube_id})
    if not current.ok or not current.json().get("items"):
        frappe.throw("This connected channel cannot manage the selected broadcast")
    snippet = current.json()["items"][0]["snippet"]
    snippet.update({"title": doc.title, "description": doc.description or "",
        "scheduledStartTime": get_datetime(doc.starts_at).replace(tzinfo=ZoneInfo("Asia/Colombo")).astimezone(timezone.utc).isoformat(),
        "scheduledEndTime": get_datetime(doc.ends_at).replace(tzinfo=ZoneInfo("Asia/Colombo")).astimezone(timezone.utc).isoformat()})
    # Only writable snippet keys; preserve supported existing values.
    snippet = {key: value for key, value in snippet.items() if key in ("title", "description", "scheduledStartTime", "scheduledEndTime")}
    result = requests.put("https://www.googleapis.com/youtube/v3/liveBroadcasts", timeout=20,
        headers=headers, params={"part": "snippet"}, json={"id": doc.youtube_id, "snippet": snippet})
    if not result.ok:
        frappe.throw(f"YouTube update failed (HTTP {result.status_code})")
    return {"updated": True}


@frappe.whitelist(methods=["POST"])
def transition_broadcast(session: str, status: str):
    inst, _ = identity()
    doc = scoped("IL Session", session, inst)
    _, _, room = classroom_for(doc.classroom, write=True)
    if status not in ("testing", "live", "complete") or not doc.youtube_id:
        frappe.throw("Choose a valid broadcast transition")
    result = requests.post("https://www.googleapis.com/youtube/v3/liveBroadcasts/transition", timeout=20,
        headers={"Authorization": f"Bearer {token(room.teacher)}"},
        params={"part": "status", "id": doc.youtube_id, "broadcastStatus": status})
    if not result.ok:
        frappe.throw(f"YouTube transition failed (HTTP {result.status_code}). Connect and start your encoder in YouTube Studio first.")
    if status in ("live", "complete"):
        doc.status = "Live" if status == "live" else "Completed"
        doc.save(ignore_permissions=True)
        from .notifications import classroom_event
        classroom_event(room, f"transition:{doc.name}:{status}", f"{doc.title}: {doc.status}")
    return {"status": status}


@frappe.whitelist(methods=["POST"])
def live_chat(session: str):
    """Teacher/admin-only chat reader; text-only messages, bounded cache, no DB history."""
    import time
    import math
    inst, _ = identity()
    doc = scoped("IL Session", session, inst)
    _, _, room = classroom_for(doc.classroom, write=True)
    if doc.mode != "Online" or not doc.youtube_id:
        frappe.throw("Attach an online YouTube broadcast first")
    cache_key = f"il_live_chat:{inst.name}:{doc.name}:{doc.youtube_id}"
    # Permissions are checked on every request, even when returning cached data.
    with frappe.cache.lock(cache_key + ":lock", timeout=65, blocking_timeout=2):
        state = frappe.cache.get_value(cache_key) or {}
        if state.get("next_at", 0) > time.time():
            return state["public"]
        headers = {"Authorization": f"Bearer {token(room.teacher)}"}
        chat_id = state.get("chat_id")
        try:
            if not chat_id:
                response = requests.get("https://www.googleapis.com/youtube/v3/liveBroadcasts", headers=headers,
                    params={"part": "snippet,status", "id": doc.youtube_id}, timeout=20)
                if not response.ok:
                    frappe.throw("The connected channel cannot read this broadcast")
                items = response.json().get("items", [])
                chat_id = items[0].get("snippet", {}).get("liveChatId") if items else None
                if not chat_id:
                    return {"messages": [], "ended": True, "message": "No live chat is available for this broadcast. Check its audience, live status and channel permissions."}
            params = {"liveChatId": chat_id, "part": "id,snippet,authorDetails", "maxResults": 200}
            if state.get("cursor"):
                params["pageToken"] = state["cursor"]
            response = requests.get("https://www.googleapis.com/youtube/v3/liveChat/messages", headers=headers, params=params, timeout=20)
            if not response.ok:
                frappe.throw("YouTube live chat is unavailable, ended, disabled or rate limited. Pause and try again later.")
            body = response.json()
        except (requests.RequestException, ValueError):
            frappe.throw("YouTube chat could not be reached. Try again later.")
        messages = {m["id"]: m for m in state.get("public", {}).get("messages", [])}
        for item in body.get("items", []):
            snippet = item.get("snippet", {})
            if snippet.get("type") == "messageDeletedEvent":
                messages.pop(snippet.get("messageDeletedDetails", {}).get("deletedMessageId"), None)
            elif snippet.get("displayMessage"):
                messages[item["id"]] = {"id": item["id"], "author": str(item.get("authorDetails", {}).get("displayName", "Viewer"))[:100],
                    "text": str(snippet["displayMessage"])[:2000], "published_at": snippet.get("publishedAt", "")}
        interval = max(5000, int(body.get("pollingIntervalMillis", 10000)))
        public = {"messages": list(messages.values())[-200:], "ended": bool(body.get("offlineAt")), "polling_interval_ms": interval}
        state = {"chat_id": chat_id, "cursor": body.get("nextPageToken"), "next_at": time.time() + interval / 1000, "public": public}
        frappe.cache.set_value(cache_key, state, expires_in_sec=max(600, math.ceil(interval / 1000) + 60))
        return public
