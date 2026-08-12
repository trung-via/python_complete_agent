import pytest
from unittest.mock import patch, MagicMock
from src.modules.gdrive_integrator import GDriveIntegrator

@patch('src.modules.gdrive_integrator.os.path.exists')
@patch('src.modules.gdrive_integrator.InstalledAppFlow.from_client_secrets_file')
@patch('src.modules.gdrive_integrator.build')
@patch('builtins.open', new_callable=MagicMock)
def test_gdrive_auth_success(mock_open, mock_build, mock_flow, mock_exists):
    mock_exists.side_effect = lambda x: x == "dummy.json"
    
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "test"}'
    mock_flow.return_value.run_local_server.return_value = mock_creds
    
    gdrive = GDriveIntegrator("dummy.json")
    gdrive.authenticate()
    
    mock_exists.assert_any_call("dummy.json")
    mock_flow.assert_called_once()
    mock_build.assert_called_once()
    assert gdrive.service is not None

@patch('src.modules.gdrive_integrator.os.path.exists')
def test_gdrive_auth_no_file(mock_exists):
    mock_exists.return_value = False
    
    gdrive = GDriveIntegrator("dummy.json")
    gdrive.authenticate()
    
    assert gdrive.service is None
