import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

class GDriveIntegrator:
    SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']

    def __init__(self, credentials_file: str):
        self.credentials_file = credentials_file
        self.service = None
        # Removed self.authenticate() for Lazy Auth (P0 #10)

    def authenticate(self):
        """Authenticates using OAuth2 Client ID."""
        if not os.path.exists(self.credentials_file):
            logger.warning(f"Credentials file {self.credentials_file} not found. GDrive integration will be disabled.")
            return

        creds = None
        token_path = "token.json"
        
        # The file token.json stores the user's access and refresh tokens
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            
        # If there are no (valid) credentials available, let the user log in.
        try:
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    # We will use a local server for the OAuth flow
                    creds = flow.run_local_server(port=0)
                    
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Google Drive via OAuth2.")
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Drive: {e}")

    def _get_idempotency_key(self, file_path: str) -> str:
        """Generates a stable key (hash) based on filename and contents."""
        import hashlib
        hasher = hashlib.md5()
        hasher.update(os.path.basename(file_path).encode('utf-8'))
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def upload_file(self, file_path: str, folder_id: str = None) -> str:
        """
        Uploads a file to Google Drive. 
        Returns the ID of the uploaded file, or None if it failed.
        Implements true idempotency by using appProperties (P0 #11).
        """
        if not self.service:
            logger.error("Google Drive service is not authenticated.")
            return None

        if not os.path.exists(file_path):
            logger.error(f"File to upload does not exist: {file_path}")
            return None

        file_name = os.path.basename(file_path)
        idempotency_key = self._get_idempotency_key(file_path)
        
        # Idempotency Check: Does it already exist with this exact content?
        try:
            # Query by appProperties
            query = f"appProperties has {{ key='idempotency_key' and value='{idempotency_key}' }} and trashed=false"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            response = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = response.get('files', [])
            if files:
                file_id = files[0].get('id')
                logger.info(f"File {file_name} already exists in GDrive with identical content (ID: {file_id}). Skipping upload.")
                return file_id
        except Exception as e:
            logger.warning(f"Failed to check for existing file {file_name}: {e}")

        file_metadata = {
            'name': file_name,
            'appProperties': {'idempotency_key': idempotency_key}
        }
        if folder_id:
            file_metadata['parents'] = [folder_id]

        try:
            media = MediaFileUpload(file_path, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Successfully uploaded {file_name} to Google Drive (ID: {file_id})")
            return file_id
        except Exception as e:
            logger.error(f"Failed to upload file to Google Drive: {e}")
            from googleapiclient.errors import HttpError
            from src.core.errors import AgentException
            
            if isinstance(e, HttpError):
                if e.resp.status == 429:
                    retry_after = e.resp.get('Retry-After')
                    details = {'retry_after': retry_after} if retry_after else None
                    raise AgentException(f"Google Drive Rate Limit: {e}", retryable=True, code="RATE_LIMIT", details=details)
                elif e.resp.status in [401, 403]:
                    raise AgentException(f"Google Drive Auth/Permission Error: {e}", retryable=False, code="AUTH_ERROR")
                elif e.resp.status >= 500:
                    raise AgentException(f"Google Drive Server Error: {e}", retryable=True, code="SERVER_ERROR")
            
            raise AgentException(f"Google Drive Upload Failed: {e}", retryable=True, code="UPLOAD_FAILED")

    def get_or_create_folder(self, folder_name: str, parent_id: str = None) -> str:
        """
        Finds a folder by name (and optional parent_id). If it doesn't exist, creates it.
        Returns the folder ID.
        """
        if not self.service:
            logger.error("Google Drive service is not authenticated.")
            return None
            
        try:
            # Search for the folder
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
                
            response = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = response.get('files', [])
            
            if files:
                folder_id = files[0].get('id')
                logger.info(f"Found existing GDrive folder: {folder_name} (ID: {folder_id})")
                return folder_id
                
            # If not found, create it
            logger.info(f"Creating new GDrive folder: {folder_name}")
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                folder_metadata['parents'] = [parent_id]
                
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            return folder.get('id')
            
        except Exception as e:
            logger.error(f"Error managing folder {folder_name}: {e}")
            from googleapiclient.errors import HttpError
            from src.core.errors import AgentException
            
            if isinstance(e, HttpError):
                if e.resp.status == 429:
                    retry_after = e.resp.get('Retry-After')
                    details = {'retry_after': retry_after} if retry_after else None
                    raise AgentException(f"Google Drive Rate Limit: {e}", retryable=True, code="RATE_LIMIT", details=details)
                elif e.resp.status in [401, 403]:
                    raise AgentException(f"Google Drive Auth/Permission Error: {e}", retryable=False, code="AUTH_ERROR")
                elif e.resp.status >= 500:
                    raise AgentException(f"Google Drive Server Error: {e}", retryable=True, code="SERVER_ERROR")
            
            raise AgentException(f"Google Drive Folder Error: {e}", retryable=True, code="FOLDER_ERROR")
