"""
Browser Memory - Stores and retrieves page state, credentials, and navigation history.

Provides persistent storage for:
- Login credentials (encrypted)
- Page state and DOM snapshots
- Navigation history
- Form data
- Extracted data from pages
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import hashlib
import base64

logger = logging.getLogger(__name__)


@dataclass
class CredentialEntry:
    """Stored credential with minimal sensitive data."""
    service: str
    username: str
    password_hash: str  # Never store plaintext
    url_pattern: str
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    
    def to_dict(self):
        return {
            "service": self.service,
            "username": self.username,
            "password_hash": self.password_hash,
            "url_pattern": self.url_pattern,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


@dataclass
class PageSnapshot:
    """Snapshot of page state for recovery."""
    url: str
    title: str
    html_excerpt: str  # First 5000 chars of HTML
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "url": self.url,
            "title": self.title,
            "html_excerpt": self.html_excerpt,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class NavigationRecord:
    """Record of a navigation action."""
    from_url: str
    to_url: str
    action: str  # click, form_submit, back, forward, etc.
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self):
        return {
            "from_url": self.from_url,
            "to_url": self.to_url,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_message": self.error_message,
        }


class BrowserMemory:
    """
    Persistent memory for browser sessions.
    
    Stores credentials, page state, navigation history, and extracted data.
    """

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or "browser_memory")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.credentials: Dict[str, CredentialEntry] = {}
        self.page_snapshots: Dict[str, list[PageSnapshot]] = {}  # session_id -> snapshots
        self.navigation_history: Dict[str, list[NavigationRecord]] = {}  # session_id -> records
        self.extracted_data: Dict[str, dict] = {}  # session_id -> extracted data
        
        self._load_credentials()
        logger.info(f"BrowserMemory initialized with data_dir={self.data_dir}")

    def _load_credentials(self):
        """Load credentials from storage."""
        cred_file = self.data_dir / "credentials.json"
        if not cred_file.exists():
            return

        try:
            with open(cred_file, "r") as f:
                data = json.load(f)
                for key, cred_data in data.items():
                    entry = CredentialEntry(
                        service=cred_data["service"],
                        username=cred_data["username"],
                        password_hash=cred_data["password_hash"],
                        url_pattern=cred_data["url_pattern"],
                        created_at=datetime.fromisoformat(cred_data["created_at"]),
                        last_used=datetime.fromisoformat(cred_data["last_used"]) if cred_data.get("last_used") else None,
                    )
                    self.credentials[key] = entry
            logger.info(f"Loaded {len(self.credentials)} credentials")
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")

    def _save_credentials(self):
        """Persist credentials to storage."""
        try:
            cred_file = self.data_dir / "credentials.json"
            data = {k: v.to_dict() for k, v in self.credentials.items()}
            with open(cred_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def store_credential(
        self,
        service: str,
        username: str,
        password: str,
        url_pattern: str,
    ) -> str:
        """
        Store credentials securely (password is hashed).
        
        Args:
            service: Service name (e.g., 'linkedin', 'uber')
            username: Username/email
            password: Password (will be hashed)
            url_pattern: URL pattern for matching (e.g., 'linkedin.com')
            
        Returns:
            Credential key
        """
        # Hash password (simple; in production use proper secrets management)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Create unique key
        key = f"{service}:{username}"
        
        entry = CredentialEntry(
            service=service,
            username=username,
            password_hash=password_hash,
            url_pattern=url_pattern,
        )
        
        self.credentials[key] = entry
        self._save_credentials()
        
        logger.info(f"Stored credential for {service}:{username}")
        return key

    def get_credential(self, service: str) -> Optional[CredentialEntry]:
        """Get credential for a service."""
        for key, entry in self.credentials.items():
            if entry.service.lower() == service.lower():
                entry.last_used = datetime.now()
                self._save_credentials()
                return entry
        return None

    def record_page_snapshot(self, session_id: str, snapshot: PageSnapshot):
        """Record a page snapshot for recovery."""
        if session_id not in self.page_snapshots:
            self.page_snapshots[session_id] = []
        
        self.page_snapshots[session_id].append(snapshot)
        # Keep only last 50 snapshots per session
        self.page_snapshots[session_id] = self.page_snapshots[session_id][-50:]

    def get_latest_snapshot(self, session_id: str) -> Optional[PageSnapshot]:
        """Get the latest page snapshot for a session."""
        if session_id not in self.page_snapshots or not self.page_snapshots[session_id]:
            return None
        return self.page_snapshots[session_id][-1]

    def record_navigation(self, session_id: str, record: NavigationRecord):
        """Record a navigation action."""
        if session_id not in self.navigation_history:
            self.navigation_history[session_id] = []
        
        self.navigation_history[session_id].append(record)
        # Keep only last 200 records per session
        self.navigation_history[session_id] = self.navigation_history[session_id][-200:]

    def get_navigation_history(self, session_id: str, limit: int = 20) -> list[NavigationRecord]:
        """Get recent navigation history."""
        if session_id not in self.navigation_history:
            return []
        return self.navigation_history[session_id][-limit:]

    def store_extracted_data(self, session_id: str, data_key: str, data: Any):
        """Store extracted data from pages."""
        if session_id not in self.extracted_data:
            self.extracted_data[session_id] = {}
        
        self.extracted_data[session_id][data_key] = {
            "value": data,
            "timestamp": datetime.now().isoformat(),
        }

    def get_extracted_data(self, session_id: str, data_key: str = None) -> Any:
        """Get extracted data."""
        if session_id not in self.extracted_data:
            return None
        
        if data_key is None:
            return self.extracted_data[session_id]
        
        entry = self.extracted_data[session_id].get(data_key)
        return entry["value"] if entry else None

    def clear_session_memory(self, session_id: str):
        """Clear memory for a session."""
        self.page_snapshots.pop(session_id, None)
        self.navigation_history.pop(session_id, None)
        self.extracted_data.pop(session_id, None)
        logger.info(f"Cleared memory for session {session_id}")
