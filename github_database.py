from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests


class GitHubDatabaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubDatabaseConfig:
    token: str
    owner: str
    repo: str
    branch: str = "main"
    root_path: str = "Database"

    @property
    def normalized_root(self) -> str:
        return self.root_path.strip("/")


class GitHubDatabase:
    API_ROOT = "https://api.github.com"

    def __init__(self, config: GitHubDatabaseConfig, timeout_s: int = 30) -> None:
        self.config = config
        self.timeout_s = timeout_s
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {config.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "BikePowerCalculator",
        })

    def _repo_url(self) -> str:
        return f"{self.API_ROOT}/repos/{quote(self.config.owner)}/{quote(self.config.repo)}"

    def _contents_url(self, path: str) -> str:
        encoded = "/".join(quote(part, safe="") for part in path.strip("/").split("/"))
        return f"{self._repo_url()}/contents/{encoded}"

    def _request(self, method: str, url: str, **kwargs):
        try:
            response = self.session.request(method, url, timeout=self.timeout_s, **kwargs)
        except requests.RequestException as exc:
            raise GitHubDatabaseError(f"GitHub ist nicht erreichbar: {exc}") from exc
        if response.status_code >= 400:
            try:
                message = response.json().get("message", response.text)
            except Exception:
                message = response.text
            raise GitHubDatabaseError(f"GitHub API {response.status_code}: {message}")
        return response

    def test_connection(self) -> dict[str, Any]:
        data = self._request("GET", self._repo_url()).json()
        return {
            "full_name": data.get("full_name"),
            "private": bool(data.get("private")),
            "default_branch": data.get("default_branch"),
        }

    def get_file(self, path: str) -> tuple[bytes, str] | None:
        response = self.session.get(
            self._contents_url(path),
            params={"ref": self.config.branch},
            timeout=self.timeout_s,
        )
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            try:
                message = response.json().get("message", response.text)
            except Exception:
                message = response.text
            raise GitHubDatabaseError(f"GitHub API {response.status_code}: {message}")
        payload = response.json()
        return base64.b64decode(payload.get("content", "")), payload.get("sha", "")

    def put_file(self, path: str, content: bytes, message: str, sha: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content).decode("ascii"),
            "branch": self.config.branch,
        }
        if sha:
            payload["sha"] = sha
        return self._request("PUT", self._contents_url(path), json=payload).json()

    def get_json(self, path: str) -> tuple[Any, str] | None:
        loaded = self.get_file(path)
        if loaded is None:
            return None
        content, sha = loaded
        return json.loads(content.decode("utf-8")), sha

    def put_json(self, path: str, data: Any, message: str, sha: str | None = None) -> dict[str, Any]:
        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        return self.put_file(path, content, message, sha)

    @property
    def index_path(self) -> str:
        return f"{self.config.normalized_root}/index.json"

    def initialize(self) -> dict[str, Any]:
        existing = self.get_json(self.index_path)
        if existing is not None:
            return existing[0]
        index = {
            "schema_version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "events": [],
        }
        self.put_json(self.index_path, index, "Initialize Bike Power Calculator database")
        return index

    def load_index(self) -> tuple[dict[str, Any], str | None]:
        loaded = self.get_json(self.index_path)
        if loaded is None:
            return self.initialize(), None
        index, sha = loaded
        index.setdefault("schema_version", 1)
        index.setdefault("events", [])
        return index, sha

    def _event_path(self, event_id: str, filename: str) -> str:
        return f"{self.config.normalized_root}/Events/{event_id}/{filename}"

    def list_events(self) -> list[dict[str, Any]]:
        return list(self.load_index()[0].get("events", []))

    def create_event(self, *, name: str, event_date: str = "", location: str = "", sport: str = "Triathlon", tags: list[str] | None = None, notes: str = "", settings: dict[str, Any] | None = None) -> dict[str, Any]:
        event_id = uuid.uuid4().hex[:8]
        now = datetime.now(timezone.utc).isoformat()
        event = {
            "schema_version": 1,
            "id": event_id,
            "name": name.strip(),
            "date": event_date,
            "location": location.strip(),
            "sport": sport.strip(),
            "tags": tags or [],
            "notes": notes.strip(),
            "created_at": now,
            "updated_at": now,
        }
        self.put_json(self._event_path(event_id, "event.json"), event, f"Create event: {event['name']}")
        self.put_json(self._event_path(event_id, "settings.json"), settings or {}, f"Save settings: {event['name']}")
        index, sha = self.load_index()
        index["events"] = [e for e in index.get("events", []) if e.get("id") != event_id]
        index["events"].append({
            "id": event_id,
            "name": event["name"],
            "date": event["date"],
            "location": event["location"],
            "sport": event["sport"],
            "tags": event["tags"],
            "updated_at": now,
        })
        index["events"].sort(key=lambda e: (e.get("date") or "", e.get("name") or ""), reverse=True)
        index["updated_at"] = now
        self.put_json(self.index_path, index, f"Update database index: add {event['name']}", sha)
        return event

    def load_event(self, event_id: str) -> dict[str, Any]:
        loaded = self.get_json(self._event_path(event_id, "event.json"))
        if loaded is None:
            raise GitHubDatabaseError(f"Event {event_id} wurde nicht gefunden.")
        return loaded[0]

    def load_settings(self, event_id: str) -> dict[str, Any]:
        loaded = self.get_json(self._event_path(event_id, "settings.json"))
        return {} if loaded is None else loaded[0]
