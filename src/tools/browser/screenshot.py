import uuid
from typing import Optional, Dict, Any, Type
from pydantic import BaseModel
import os

from src.tools.browser.base import BaseBrowserTool
from src.browser.session import BrowserSession

class ScreenshotArgs(BaseModel):
    pass

class ScreenshotTool(BaseBrowserTool):
    @property
    def name(self) -> str:
        return "browser.screenshot"
        
    @property
    def description(self) -> str:
        return "Take a screenshot of the current page. Returns the artifact ID representing the image."
        
    @property
    def retryable(self) -> bool:
        return True
        
    @property
    def idempotent(self) -> bool:
        return True

    def get_arguments_schema(self) -> Type[BaseModel]:
        return ScreenshotArgs

    async def execute_browser_action(self, session: BrowserSession, parsed_args: ScreenshotArgs) -> Optional[Dict[str, Any]]:
        image_bytes = await session.screenshot()
        
        # In a real system, this would upload to an ArtifactStore and return an ID.
        # For Phase 3 MVP, we save it locally and return the path.
        artifact_id = f"screenshot_{uuid.uuid4().hex[:8]}.png"
        
        # Make a dir in current workspace
        artifacts_dir = os.path.join(os.getcwd(), "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        
        artifact_path = os.path.join(artifacts_dir, artifact_id)
        with open(artifact_path, "wb") as f:
            f.write(image_bytes)
            
        return {
            "artifact_id": artifact_id,
            "path": artifact_path,
            "mime_type": "image/png"
        }
