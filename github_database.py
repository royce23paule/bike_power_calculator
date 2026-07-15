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


    def delete_file(self, path: str, message: str) -> None:
        loaded = self.get_file(path)
        if loaded is None:
            return
        _, sha = loaded
        payload = {
            "message": message,
            "sha": sha,
            "branch": self.config.branch,
        }
        self._request("DELETE", self._contents_url(path), json=payload)

    def list_directory(self, path: str) -> list[dict[str, Any]]:
        response = self.session.get(
            self._contents_url(path),
            params={"ref": self.config.branch},
            timeout=self.timeout_s,
        )
        if response.status_code == 404:
            return []
        if response.status_code >= 400:
            try:
                message = response.json().get("message", response.text)
            except Exception:
                message = response.text
            raise GitHubDatabaseError(
                f"GitHub API {response.status_code}: {message}"
            )
        payload = response.json()
        return payload if isinstance(payload, list) else []


    def _git_url(self, suffix: str) -> str:
        return f"{self._repo_url()}/git/{suffix.lstrip('/')}"

    def _get_branch_commit_and_tree(self) -> tuple[str, str]:
        ref_response = self._request(
            "GET",
            self._git_url(f"ref/heads/{quote(self.config.branch, safe='')}"),
        )
        commit_sha = ref_response.json()["object"]["sha"]

        commit_response = self._request(
            "GET",
            self._git_url(f"commits/{commit_sha}"),
        )
        tree_sha = commit_response.json()["tree"]["sha"]
        return commit_sha, tree_sha

    def put_file_via_git_data(
        self,
        path: str,
        content: bytes,
        message: str,
    ) -> dict[str, Any]:
        """Writes a file by creating a blob, tree and commit.

        This is more robust than the repository contents endpoint for larger
        binary FIT/GPX files because the file is written as a raw Git object.
        """
        commit_sha, base_tree_sha = self._get_branch_commit_and_tree()

        blob_response = self._request(
            "POST",
            self._git_url("blobs"),
            json={
                "content": base64.b64encode(content).decode("ascii"),
                "encoding": "base64",
            },
        )
        blob_sha = blob_response.json()["sha"]

        tree_response = self._request(
            "POST",
            self._git_url("trees"),
            json={
                "base_tree": base_tree_sha,
                "tree": [
                    {
                        "path": path.strip("/"),
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_sha,
                    }
                ],
            },
        )
        new_tree_sha = tree_response.json()["sha"]

        commit_response = self._request(
            "POST",
            self._git_url("commits"),
            json={
                "message": message,
                "tree": new_tree_sha,
                "parents": [commit_sha],
            },
        )
        new_commit_sha = commit_response.json()["sha"]

        ref_response = self._request(
            "PATCH",
            self._git_url(f"refs/heads/{quote(self.config.branch, safe='')}"),
            json={
                "sha": new_commit_sha,
                "force": False,
            },
        )
        return {
            "commit": commit_response.json(),
            "ref": ref_response.json(),
            "blob_sha": blob_sha,
        }

    def save_event_file(
        self,
        event_id: str,
        filename: str,
        content: bytes,
        message: str | None = None,
    ) -> None:
        safe_name = filename.split("/")[-1]
        path = self._event_path(event_id, safe_name)
        commit_message = message or f"Save {safe_name} for event {event_id}"

        # The repository contents endpoint is convenient for small text files.
        # Larger binary files use Git blobs/trees/commits instead.
        if len(content) >= 750 * 1024:
            self.put_file_via_git_data(
                path=path,
                content=content,
                message=commit_message,
            )
            return

        existing = self.get_file(path)
        existing_sha = existing[1] if existing else None
        self.put_file(
            path,
            content,
            commit_message,
            existing_sha,
        )

    def load_event_file(self, event_id: str, filename: str) -> bytes:
        safe_name = filename.split("/")[-1]
        loaded = self.get_file(self._event_path(event_id, safe_name))
        if loaded is None:
            raise GitHubDatabaseError(
                f"Datei {safe_name} wurde im Event nicht gefunden."
            )
        return loaded[0]

    def list_event_files(self, event_id: str) -> list[dict[str, Any]]:
        path = f"{self.config.normalized_root}/Events/{event_id}"
        items = self.list_directory(path)
        return [
            {
                "name": item.get("name"),
                "path": item.get("path"),
                "size": item.get("size", 0),
                "type": item.get("type"),
                "sha": item.get("sha"),
                "download_url": item.get("download_url"),
            }
            for item in items
            if item.get("type") == "file"
        ]

    def update_event(
        self,
        event_id: str,
        *,
        name: str,
        event_date: str = "",
        location: str = "",
        sport: str = "Triathlon",
        tags: list[str] | None = None,
        notes: str = "",
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        loaded = self.get_json(self._event_path(event_id, "event.json"))
        if loaded is None:
            raise GitHubDatabaseError(f"Event {event_id} wurde nicht gefunden.")

        event, event_sha = loaded
        now = datetime.now(timezone.utc).isoformat()
        event.update(
            {
                "name": name.strip(),
                "date": event_date,
                "location": location.strip(),
                "sport": sport.strip(),
                "tags": tags or [],
                "notes": notes.strip(),
                "updated_at": now,
            }
        )
        self.put_json(
            self._event_path(event_id, "event.json"),
            event,
            f"Update event: {event['name']}",
            event_sha,
        )

        if settings is not None:
            settings_path = self._event_path(event_id, "settings.json")
            existing = self.get_json(settings_path)
            settings_sha = existing[1] if existing else None
            self.put_json(
                settings_path,
                settings,
                f"Update settings for event: {event['name']}",
                settings_sha,
            )

        index, index_sha = self.load_index()
        for entry in index.get("events", []):
            if entry.get("id") == event_id:
                entry.update(
                    {
                        "name": event["name"],
                        "date": event["date"],
                        "location": event["location"],
                        "sport": event["sport"],
                        "tags": event["tags"],
                        "updated_at": now,
                    }
                )
                break
        index["events"].sort(
            key=lambda item: (
                item.get("date") or "",
                item.get("name") or "",
            ),
            reverse=True,
        )
        index["updated_at"] = now
        self.put_json(
            self.index_path,
            index,
            f"Update database index: edit {event['name']}",
            index_sha,
        )
        return event

    def delete_event(self, event_id: str) -> None:
        event = self.load_event(event_id)
        path = f"{self.config.normalized_root}/Events/{event_id}"
        items = self.list_directory(path)

        # Files must be deleted one by one through GitHub Contents API.
        for item in items:
            if item.get("type") == "file":
                self.delete_file(
                    item["path"],
                    f"Delete {item.get('name')} from event {event.get('name')}",
                )

        index, index_sha = self.load_index()
        index["events"] = [
            entry for entry in index.get("events", [])
            if entry.get("id") != event_id
        ]
        index["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.put_json(
            self.index_path,
            index,
            f"Update database index: delete {event.get('name')}",
            index_sha,
        )

    def duplicate_event(
        self,
        event_id: str,
        new_name: str | None = None,
    ) -> dict[str, Any]:
        source_event = self.load_event(event_id)
        source_settings = self.load_settings(event_id)
        copied = self.create_event(
            name=new_name or f"{source_event.get('name', 'Event')} (Kopie)",
            event_date=source_event.get("date", ""),
            location=source_event.get("location", ""),
            sport=source_event.get("sport", "Triathlon"),
            tags=list(source_event.get("tags", [])),
            notes=source_event.get("notes", ""),
            settings=source_settings,
        )

        for file_info in self.list_event_files(event_id):
            filename = file_info.get("name")
            if filename in {"event.json", "settings.json"}:
                continue
            content = self.load_event_file(event_id, filename)
            self.save_event_file(
                copied["id"],
                filename,
                content,
                f"Copy {filename} to duplicated event {copied['name']}",
            )
        return copied

    def find_events_by_name(self, name: str) -> list[dict[str, Any]]:
        normalized = name.strip().casefold()
        return [
            event for event in self.list_events()
            if str(event.get("name", "")).strip().casefold() == normalized
        ]

    def load_settings(self, event_id: str) -> dict[str, Any]:
        loaded = self.get_json(self._event_path(event_id, "settings.json"))
        return {} if loaded is None else loaded[0]
