from __future__ import annotations

from typing import Tuple
from src.integrations.google_drive.protocols import GoogleDriveClient, GoogleDriveFolderResolver

class SimpleFolderResolver(GoogleDriveFolderResolver):
    """
    Default FolderResolver implementation.
    Resolves nested folder paths iteratively using GoogleDriveClient.
    """
    def __init__(self, client: GoogleDriveClient):
        self.client = client

    async def resolve(self, *, root_folder_id: str, path: Tuple[str, ...]) -> str:
        current_id = root_folder_id
        for folder_name in path:
            if not folder_name:
                continue
            current_id = await self.client.create_folder(
                parent_folder_id=current_id,
                name=folder_name
            )
        return current_id
