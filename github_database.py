from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import tempfile
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests
from pathlib import Path


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
        self.put_json(
            self._event_path(event_id, "event.json"),
            event,
            f"Create event: {event['name']}",
        )
        if settings is not None:
            self.put_json(
                self._event_path(event_id, "settings.json"),
                settings,
                f"Save settings: {event['name']}",
            )
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



    def _request_git_stage(
        self,
        stage: str,
        method: str,
        url: str,
        **kwargs,
    ):
        """Git request with stage-specific diagnostics and safe error output."""
        try:
            response = self.session.request(
                method,
                url,
                timeout=self.timeout_s,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise GitHubDatabaseError(
                f"Git-Upload fehlgeschlagen bei „{stage}“: "
                f"GitHub ist nicht erreichbar: {exc}"
            ) from exc

        if response.status_code >= 400:
            content_type = response.headers.get("content-type", "unbekannt")
            request_id = response.headers.get("x-github-request-id", "—")
            try:
                parsed = response.json()
                message = parsed.get("message", str(parsed))
            except Exception:
                text = response.text.strip().replace("\n", " ")
                message = text[:500] if text else "Leere Antwort"

            raise GitHubDatabaseError(
                f"Git-Upload fehlgeschlagen bei „{stage}“. "
                f"HTTP {response.status_code}; Content-Type: {content_type}; "
                f"GitHub Request-ID: {request_id}; Antwort: {message}"
            )
        return response

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
        """Writes a file through Git blobs, trees, commits and references."""
        commit_sha, base_tree_sha = self._get_branch_commit_and_tree()

        blob_payload = {
            "content": base64.b64encode(content).decode("ascii"),
            "encoding": "base64",
        }
        blob_response = self._request_git_stage(
            "Blob erzeugen",
            "POST",
            self._git_url("blobs"),
            json=blob_payload,
        )
        blob_sha = blob_response.json()["sha"]

        tree_response = self._request_git_stage(
            "Tree erzeugen",
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

        commit_response = self._request_git_stage(
            "Commit erzeugen",
            "POST",
            self._git_url("commits"),
            json={
                "message": message,
                "tree": new_tree_sha,
                "parents": [commit_sha],
            },
        )
        new_commit_sha = commit_response.json()["sha"]

        ref_response = self._request_git_stage(
            "Branch aktualisieren",
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



    def _git_auth_environment(self) -> dict[str, str]:
        """Creates Git HTTP authentication without embedding the token in the URL."""
        credentials = base64.b64encode(
            f"x-access-token:{self.config.token}".encode("utf-8")
        ).decode("ascii")

        environment = os.environ.copy()
        environment.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.extraHeader",
                "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {credentials}",
            }
        )
        return environment

    def _run_git(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        timeout_s: int = 180,
    ) -> subprocess.CompletedProcess:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=cwd,
                env=self._git_auth_environment(),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except FileNotFoundError as exc:
            raise GitHubDatabaseError(
                "Das Programm `git` ist in der Streamlit-Umgebung nicht verfügbar."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise GitHubDatabaseError(
                f"Git-Befehl wurde nach {timeout_s} Sekunden abgebrochen."
            ) from exc

        if completed.returncode != 0:
            error_text = (completed.stderr or completed.stdout or "").strip()
            # Defensive token redaction in case Git ever echoes credentials.
            error_text = error_text.replace(self.config.token, "***")
            raise GitHubDatabaseError(
                f"Git-Befehl fehlgeschlagen: {' '.join(args[:2])}. "
                f"{error_text[:1200]}"
            )
        return completed

    def put_file_via_git_push(
        self,
        path: str,
        content: bytes,
        message: str,
    ) -> None:
        """Stores a binary file using a normal Git commit and HTTPS push."""
        repository_url = (
            f"https://github.com/{self.config.owner}/{self.config.repo}.git"
        )

        with tempfile.TemporaryDirectory(prefix="bike-power-git-") as temp_dir:
            self._run_git(
                [
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    self.config.branch,
                    repository_url,
                    temp_dir,
                ],
                timeout_s=180,
            )

            target = Path(temp_dir) / Path(path.strip("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

            self._run_git(
                ["config", "user.name", "Bike Power Calculator"],
                cwd=temp_dir,
            )
            self._run_git(
                ["config", "user.email", "bike-power-calculator@users.noreply.github.com"],
                cwd=temp_dir,
            )
            self._run_git(["add", "--", path.strip("/")], cwd=temp_dir)

            status = self._run_git(
                ["status", "--porcelain", "--", path.strip("/")],
                cwd=temp_dir,
            )
            if not status.stdout.strip():
                return

            self._run_git(["commit", "-m", message], cwd=temp_dir)

            # Rebase once to reduce the chance of conflicts when another API
            # operation updated index.json shortly before this upload.
            self._run_git(
                ["pull", "--rebase", "origin", self.config.branch],
                cwd=temp_dir,
            )
            self._run_git(
                ["push", "origin", f"HEAD:{self.config.branch}"],
                cwd=temp_dir,
                timeout_s=180,
            )

    def get_file_raw(self, path: str) -> bytes | None:
        """Loads repository content using GitHub's raw media type."""
        response = self.session.get(
            self._contents_url(path),
            params={"ref": self.config.branch},
            headers={
                "Accept": "application/vnd.github.raw+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=self.timeout_s,
        )
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            try:
                message = response.json().get("message", response.text)
            except Exception:
                message = response.text
            raise GitHubDatabaseError(
                f"GitHub API {response.status_code}: {message}"
            )
        return response.content


    CHUNK_SIZE_BYTES = 48 * 1024

    def _chunk_directory_path(self, event_id: str, filename: str) -> str:
        safe_name = filename.split("/")[-1]
        return (
            f"{self.config.normalized_root}/Events/{event_id}/"
            f".chunks/{quote(safe_name, safe='')}"
        )

    def _chunk_manifest_path(self, event_id: str, filename: str) -> str:
        return f"{self._chunk_directory_path(event_id, filename)}/manifest.json"

    def _is_chunked_file(self, event_id: str, filename: str) -> bool:
        return self.get_file(self._chunk_manifest_path(event_id, filename)) is not None

    def _save_chunked_file(
        self,
        event_id: str,
        filename: str,
        content: bytes,
        message: str,
    ) -> None:
        safe_name = filename.split("/")[-1]
        chunk_dir = self._chunk_directory_path(event_id, safe_name)
        chunks = [
            content[offset: offset + self.CHUNK_SIZE_BYTES]
            for offset in range(0, len(content), self.CHUNK_SIZE_BYTES)
        ]

        # Existing chunks may be overwritten safely. Obsolete trailing chunks
        # from an older larger version are removed after the new manifest exists.
        existing_items = self.list_directory(chunk_dir)
        existing_names = {
            item.get("name")
            for item in existing_items
            if item.get("type") == "file"
        }

        chunk_names = []
        for index, chunk in enumerate(chunks):
            chunk_name = f"part-{index:05d}.bin"
            chunk_names.append(chunk_name)
            chunk_path = f"{chunk_dir}/{chunk_name}"
            existing = self.get_file(chunk_path)
            existing_sha = existing[1] if existing else None
            try:
                self.put_file(
                    chunk_path,
                    chunk,
                    f"{message} · chunk {index + 1}/{len(chunks)}",
                    existing_sha,
                )
            except GitHubDatabaseError as exc:
                raise GitHubDatabaseError(
                    f"Mehrteiliger Upload fehlgeschlagen bei Teil "
                    f"{index + 1}/{len(chunks)} "
                    f"({len(chunk)} Bytes): {exc}"
                ) from exc

        manifest = {
            "schema_version": 1,
            "storage": "chunked",
            "filename": safe_name,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "chunk_size_bytes": self.CHUNK_SIZE_BYTES,
            "chunks": chunk_names,
        }
        manifest_path = self._chunk_manifest_path(event_id, safe_name)
        existing_manifest = self.get_json(manifest_path)
        manifest_sha = existing_manifest[1] if existing_manifest else None
        self.put_json(
            manifest_path,
            manifest,
            f"{message} · manifest",
            manifest_sha,
        )

        # Remove chunks no longer referenced by the current manifest.
        for old_name in existing_names:
            if old_name == "manifest.json" or old_name in chunk_names:
                continue
            self.delete_file(
                f"{chunk_dir}/{old_name}",
                f"Remove obsolete chunk {old_name} for {safe_name}",
            )

    def _load_chunked_file(self, event_id: str, filename: str) -> bytes:
        loaded_manifest = self.get_json(
            self._chunk_manifest_path(event_id, filename)
        )
        if loaded_manifest is None:
            raise GitHubDatabaseError(
                f"Manifest für {filename} wurde nicht gefunden."
            )

        manifest, _ = loaded_manifest
        content_parts = []
        chunk_dir = self._chunk_directory_path(event_id, filename)
        for chunk_name in manifest.get("chunks", []):
            loaded = self.get_file(f"{chunk_dir}/{chunk_name}")
            if loaded is None:
                raise GitHubDatabaseError(
                    f"Dateiteil {chunk_name} für {filename} fehlt."
                )
            content_parts.append(loaded[0])

        content = b"".join(content_parts)
        expected_size = int(manifest.get("size_bytes", -1))
        expected_hash = str(manifest.get("sha256", ""))

        if expected_size >= 0 and len(content) != expected_size:
            raise GitHubDatabaseError(
                f"Dateigröße von {filename} stimmt nach dem Laden nicht."
            )
        if expected_hash and hashlib.sha256(content).hexdigest() != expected_hash:
            raise GitHubDatabaseError(
                f"Prüfsumme von {filename} stimmt nach dem Laden nicht."
            )
        return content


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
        suffix = safe_name.lower().rsplit(".", 1)[-1] if "." in safe_name else ""

        # Binary route/activity files use an actual Git commit and push. This
        # avoids Base64 JSON requests through the Streamlit/GitHub REST path.
        if suffix in {"fit", "gpx"} or len(content) > 1024 * 1024:
            self.put_file_via_git_push(
                path=path,
                content=content,
                message=commit_message,
            )
            return

        existing = self.get_file(path)
        existing_sha = existing[1] if existing else None
        self.put_file(path, content, commit_message, existing_sha)

    def load_event_file(self, event_id: str, filename: str) -> bytes:
        safe_name = filename.split("/")[-1]

        direct_content = self.get_file_raw(
            self._event_path(event_id, safe_name)
        )
        if direct_content is not None:
            return direct_content

        # Backward compatibility for files written by versions 3.1.4/3.1.5.
        if self._is_chunked_file(event_id, safe_name):
            return self._load_chunked_file(event_id, safe_name)

        raise GitHubDatabaseError(
            f"Datei {safe_name} wurde im Event nicht gefunden."
        )

    def list_event_files(self, event_id: str) -> list[dict[str, Any]]:
        path = f"{self.config.normalized_root}/Events/{event_id}"
        items = self.list_directory(path)

        result = [
            {
                "name": item.get("name"),
                "path": item.get("path"),
                "size": item.get("size", 0),
                "type": item.get("type"),
                "sha": item.get("sha"),
                "download_url": item.get("download_url"),
                "storage": "direct",
            }
            for item in items
            if item.get("type") == "file"
        ]

        chunks_root = f"{path}/.chunks"
        chunk_directories = self.list_directory(chunks_root)
        for directory in chunk_directories:
            if directory.get("type") != "dir":
                continue
            manifest_path = f"{directory.get('path')}/manifest.json"
            loaded = self.get_json(manifest_path)
            if loaded is None:
                continue
            manifest, _ = loaded
            result.append(
                {
                    "name": manifest.get("filename", directory.get("name")),
                    "path": directory.get("path"),
                    "size": manifest.get("size_bytes", 0),
                    "type": "file",
                    "sha": manifest.get("sha256"),
                    "download_url": None,
                    "storage": "chunked",
                }
            )

        result.sort(key=lambda item: str(item.get("name", "")).lower())
        return result


    def delete_event_file(self, event_id: str, filename: str) -> None:
        safe_name = filename.split("/")[-1]

        if self._is_chunked_file(event_id, safe_name):
            chunk_dir = self._chunk_directory_path(event_id, safe_name)
            for item in self.list_directory(chunk_dir):
                if item.get("type") == "file":
                    self.delete_file(
                        item["path"],
                        f"Delete chunked file {safe_name}",
                    )
            return

        self.delete_file(
            self._event_path(event_id, safe_name),
            f"Delete {safe_name} from event {event_id}",
        )

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


    def _calculation_path(
        self,
        event_id: str,
        calculation_id: str,
        filename: str,
    ) -> str:
        return (
            f"{self.config.normalized_root}/Events/{event_id}/"
            f"calculations/{calculation_id}/{filename}"
        )

    def save_calculation(
        self,
        event_id: str,
        *,
        name: str,
        calculation_type: str,
        settings: dict[str, Any],
        result: dict[str, Any],
        profiler: dict[str, Any] | None = None,
        run_log: str = "",
        pdf_content: bytes | None = None,
        pdf_filename: str | None = None,
        html_content: bytes | None = None,
        html_filename: str | None = None,
    ) -> dict[str, Any]:
        calculation_id = uuid.uuid4().hex[:10]
        now = datetime.now(timezone.utc).isoformat()
        event = self.load_event(event_id)

        metadata = {
            "schema_version": 1,
            "id": calculation_id,
            "event_id": event_id,
            "name": name.strip() or f"Berechnung {now[:19]}",
            "type": calculation_type,
            "created_at": now,
            "app_version": result.get("app_version"),
            "engine_version": result.get("engine_version"),
            "summary": {
                "title": result.get("title"),
                "distance_km": result.get("distance_km"),
                "duration_s": result.get("duration_s"),
                "average_speed_kmh": result.get("average_speed_kmh"),
                "average_power_w": (
                    result.get("average_power_w")
                    if result.get("average_power_w") is not None
                    else result.get("calibration_ap")
                ),
                "normalized_power_w": (
                    result.get("normalized_power_w")
                    if result.get("normalized_power_w") is not None
                    else result.get("calibration_np")
                ),
                "cda": result.get("calibration_cda"),
            },
            "files": [
                "calculation.json",
                "settings_snapshot.json",
                "result.json",
                "profiler.json",
                "run_log.txt",
            ],
        }

        if pdf_content is not None and pdf_filename:
            metadata["files"].append(pdf_filename)
        if html_content is not None and html_filename:
            metadata["files"].append(html_filename)

        base_path = (
            f"{self.config.normalized_root}/Events/{event_id}/"
            f"calculations/{calculation_id}"
        )

        payloads: list[tuple[str, bytes]] = [
            (
                f"{base_path}/calculation.json",
                json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
            ),
            (
                f"{base_path}/settings_snapshot.json",
                json.dumps(settings, ensure_ascii=False, indent=2).encode("utf-8"),
            ),
            (
                f"{base_path}/result.json",
                json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"),
            ),
            (
                f"{base_path}/profiler.json",
                json.dumps(profiler or {}, ensure_ascii=False, indent=2).encode("utf-8"),
            ),
            (
                f"{base_path}/run_log.txt",
                (run_log or "").encode("utf-8"),
            ),
        ]

        if pdf_content is not None and pdf_filename:
            payloads.append((f"{base_path}/{pdf_filename}", pdf_content))
        if html_content is not None and html_filename:
            payloads.append((f"{base_path}/{html_filename}", html_content))

        # One clone/commit/push stores the complete calculation atomically.
        repository_url = (
            f"https://github.com/{self.config.owner}/{self.config.repo}.git"
        )
        with tempfile.TemporaryDirectory(prefix="bike-power-calc-") as temp_dir:
            self._run_git(
                [
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    self.config.branch,
                    repository_url,
                    temp_dir,
                ],
                timeout_s=180,
            )
            for relative_path, content in payloads:
                target = Path(temp_dir) / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)

            self._run_git(
                ["config", "user.name", "Bike Power Calculator"],
                cwd=temp_dir,
            )
            self._run_git(
                [
                    "config",
                    "user.email",
                    "bike-power-calculator@users.noreply.github.com",
                ],
                cwd=temp_dir,
            )
            self._run_git(
                ["add", "--", base_path],
                cwd=temp_dir,
            )
            self._run_git(
                [
                    "commit",
                    "-m",
                    f"Save calculation: {metadata['name']} ({event.get('name')})",
                ],
                cwd=temp_dir,
            )
            self._run_git(
                ["pull", "--rebase", "origin", self.config.branch],
                cwd=temp_dir,
            )
            self._run_git(
                ["push", "origin", f"HEAD:{self.config.branch}"],
                cwd=temp_dir,
                timeout_s=180,
            )

        return metadata


    def save_named_settings(
        self,
        event_id: str,
        filename: str,
        settings: dict[str, Any],
    ) -> str:
        safe_name = filename.strip()
        if not safe_name.lower().endswith(".json"):
            safe_name += ".json"
        safe_name = safe_name.replace("/", "_").replace("\\", "_")
        if safe_name in {"event.json", "calculation.json", "result.json"}:
            raise GitHubDatabaseError(
                f"Der Dateiname {safe_name} ist reserviert."
            )

        path = self._event_path(event_id, safe_name)
        existing = self.get_json(path)
        existing_sha = existing[1] if existing else None
        self.put_json(
            path,
            settings,
            f"Save settings file: {safe_name}",
            existing_sha,
        )
        return safe_name

    def load_calculation_metadata(
        self,
        event_id: str,
        calculation_id: str,
    ) -> dict[str, Any]:
        return self.load_calculation_json(
            event_id,
            calculation_id,
            "calculation.json",
        )

    def load_calculation_json(
        self,
        event_id: str,
        calculation_id: str,
        filename: str,
    ) -> dict[str, Any]:
        path = self._calculation_path(event_id, calculation_id, filename)
        content = self.get_file_raw(path)
        if content is None:
            raise GitHubDatabaseError(
                f"{filename} wurde in der Berechnung nicht gefunden."
            )
        try:
            return json.loads(content.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise GitHubDatabaseError(
                f"{filename} ist keine gültige UTF-8-Datei."
            ) from exc
        except json.JSONDecodeError as exc:
            preview = content[:120].decode("utf-8", errors="replace").replace("\n", " ")
            raise GitHubDatabaseError(
                f"{filename} enthält kein gültiges JSON. "
                f"Fehler an Position {exc.pos}; Dateianfang: {preview!r}"
            ) from exc

    def load_calculation_text(
        self,
        event_id: str,
        calculation_id: str,
        filename: str,
    ) -> str:
        content = self.get_file_raw(
            self._calculation_path(event_id, calculation_id, filename)
        )
        if content is None:
            return ""
        return content.decode("utf-8-sig", errors="replace")

    def load_calculation_binary(
        self,
        event_id: str,
        calculation_id: str,
        filename: str,
    ) -> bytes:
        path = self._calculation_path(event_id, calculation_id, filename)
        raw = self.get_file_raw(path)
        if raw is None:
            raise GitHubDatabaseError(
                f"{filename} wurde in der Berechnung nicht gefunden."
            )
        return raw

    def list_calculations(self, event_id: str) -> list[dict[str, Any]]:
        root = (
            f"{self.config.normalized_root}/Events/{event_id}/calculations"
        )
        directories = self.list_directory(root)
        calculations = []
        for directory in directories:
            if directory.get("type") != "dir":
                continue
            metadata_path = f"{directory.get('path')}/calculation.json"
            content = self.get_file_raw(metadata_path)
            if content is None:
                continue
            try:
                metadata = json.loads(content.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            calculations.append(metadata)

        calculations.sort(
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )
        return calculations

    def find_events_by_name(self, name: str) -> list[dict[str, Any]]:
        normalized = name.strip().casefold()
        return [
            event for event in self.list_events()
            if str(event.get("name", "")).strip().casefold() == normalized
        ]

    def load_settings(self, event_id: str) -> dict[str, Any]:
        loaded = self.get_json(self._event_path(event_id, "settings.json"))
        return {} if loaded is None else loaded[0]
