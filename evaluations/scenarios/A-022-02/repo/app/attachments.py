"""Attachment storage for support tickets: one directory per ticket under a root."""

import os
import shutil

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_SUFFIXES = (".txt", ".log", ".png", ".pdf", ".csv")


class AttachmentError(ValueError):
    """Raised for attachments the store refuses to keep or serve."""


class AttachmentStore:
    """Keeps the files customers attach to a ticket and serves them back to agents."""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)

    def _ticket_dir(self, ticket_id):
        return os.path.join(self.root, f"ticket-{int(ticket_id)}")

    def _safe_name(self, name):
        """Return `name` if it is a plain file name, else raise AttachmentError."""
        if not name or name in (".", "..") or os.path.basename(name) != name or "\\" in name:
            raise AttachmentError(f"invalid attachment name: {name!r}")
        return name

    def save(self, ticket_id, name, data):
        """Store `data` (bytes) as attachment `name` of the ticket and return its size."""
        safe = self._safe_name(name)
        if not safe.lower().endswith(ALLOWED_SUFFIXES):
            raise AttachmentError(f"file type not allowed: {name!r}")
        if len(data) > MAX_BYTES:
            raise AttachmentError("attachment too large")
        directory = self._ticket_dir(ticket_id)
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, safe), "wb") as f:
            f.write(data)
        return len(data)

    def names(self, ticket_id):
        """Sorted attachment names of a ticket (empty when it has none)."""
        directory = self._ticket_dir(ticket_id)
        if not os.path.isdir(directory):
            return []
        return sorted(os.listdir(directory))

    def read(self, ticket_id, name):
        """Return the bytes of attachment `name` of the ticket.

        `name` is the file name from the download link an agent clicked.
        """
        path = os.path.join(self._ticket_dir(ticket_id), name)
        with open(path, "rb") as f:
            return f.read()

    def delete(self, ticket_id, name):
        """Remove one attachment. Returns False when it does not exist."""
        target = os.path.join(self._ticket_dir(ticket_id), self._safe_name(name))
        if not os.path.isfile(target):
            return False
        os.remove(target)
        return True

    def total_bytes(self, ticket_id):
        """Total size of a ticket's attachments."""
        directory = self._ticket_dir(ticket_id)
        return sum(os.path.getsize(os.path.join(directory, n)) for n in self.names(ticket_id))

    def purge(self, ticket_id):
        """Remove every attachment of a ticket (used when the ticket is deleted)."""
        shutil.rmtree(self._ticket_dir(ticket_id), ignore_errors=True)
