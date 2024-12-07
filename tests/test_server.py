# tests/test_server.py
import pytest
from unittest.mock import patch, MagicMock
from server_take_answer import app  # Исправленный импорт

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@patch('server_take_answer.Flow')  # Исправленный импорт в декораторах patch
@patch('server_take_answer.save_credentials')

def test_oauth2callback_success(mock_get_user_id, mock_save_credentials, mock_flow, client):
    # Настройка моков
    mock_flow_instance = MagicMock()
    mock_flow.from_client_secrets_file.return_value = mock_flow_instance
    mock_flow_instance.credentials = MagicMock()
    mock_flow_instance.credentials.token = 'mock_token'
    mock_flow_instance.credentials.refresh_token = 'mock_refresh_token'
    mock_flow_instance.credentials.token_uri = 'https://oauth2.googleapis.com/token'
    mock_flow_instance.credentials.client_id = 'mock_client_id'
    mock_flow_instance.credentials.client_secret = 'mock_client_secret'
    mock_flow_instance.credentials.scopes = ['https://www.googleapis.com/auth/gmail.readonly']

    mock_get_user_id.return_value = 12345

    # Симуляция GET-запроса на /oauth2callback с параметрами
    response = client.get('/oauth2callback?code=test_code&state=12345')

    # Проверка вызовов Flow
    mock_flow.from_client_secrets_file.assert_called_once_with(
        'client_secret3.json',
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
        redirect_uri='https://da59-5-34-215-156.ngrok-free.app/oauth2callback'
    )
    mock_flow_instance.fetch_token.assert_called_once_with(code='test_code')

    # Проверка сохранения учётных данных
    expected_credentials = {
        'token': 'mock_token',
        'refresh_token': 'mock_refresh_token',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'client_id': 'mock_client_id',
        'client_secret': 'mock_client_secret',
        'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
    }
    mock_save_credentials.assert_called_once_with(12345, 'mock_token', expected_credentials)

    # Проверка ответа сервера
    assert response.status_code == 200
    assert "Вы можете закрыть это окно и вернуться в Telegram." in response.get_data(as_text=True)

@patch('server_take_answer.Flow')  # Исправленный импорт
def test_oauth2callback_missing_params(mock_flow, client):
    # Симуляция GET-запроса без необходимых параметров
    response = client.get('/oauth2callback')

    # Проверка, что Flow не вызывается
    mock_flow.assert_not_called()

    # Проверка ответа сервера
    assert response.status_code == 400
    assert "Некорректный запрос." in response.get_data(as_text=True)

@patch('server_take_answer.Flow')  # Исправленный импорт
@patch('server_take_answer.save_credentials')

def test_oauth2callback_exception(mock_get_user_id, mock_save_credentials, mock_flow, client):
    # Настройка моков для выбрасывания исключения
    mock_flow_instance = MagicMock()
    mock_flow.from_client_secrets_file.return_value = mock_flow_instance
    mock_flow_instance.fetch_token.side_effect = Exception("Test exception")

    mock_get_user_id.return_value = 12345

    # Симуляция GET-запроса на /oauth2callback с параметрами
    response = client.get('/oauth2callback?code=test_code&state=12345')

    # Проверка, что учётные данные не сохраняются из-за исключения
    mock_save_credentials.assert_not_called()

    # Проверка ответа сервера
    assert response.status_code == 500
    assert "Произошла ошибка при авторизации." in response.get_data(as_text=True)
