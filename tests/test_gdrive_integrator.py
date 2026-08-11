import pytest
from unittest.mock import patch, MagicMock
from src.modules.gdrive_integrator import GDriveIntegrator

@patch('src.modules.gdrive_integrator.os.path.exists')
@patch('src.modules.gdrive_integrator.service_account.Credentials.from_service_account_file')
@patch('src.modules.gdrive_integrator.build')
def test_gdrive_auth_success(mock_build, mock_creds, mock_exists):
    mock_exists.return_value = True
    
    gdrive = GDriveIntegrator("dummy.json")
    
    mock_exists.assert_called_once_with("dummy.json")
    mock_creds.assert_called_once()
    mock_build.assert_called_once()
    assert gdrive.service is not None

@patch('src.modules.gdrive_integrator.os.path.exists')
def test_gdrive_auth_no_file(mock_exists):
    mock_exists.return_value = False
    
    gdrive = GDriveIntegrator("dummy.json")
    
    assert gdrive.service is None
