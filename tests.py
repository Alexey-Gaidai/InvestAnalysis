import pytest
from app import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_register(client):
    response = client.post('/register', json={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'test'
    })
    assert response.status_code == 200
    assert b'User created successfully!' in response.data


def test_get_portfolio(client):
    # Создаем пользователя и получаем его токен
    client.post('/register', json={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'test'
    })
    response = client.post('/login', headers={
        'Authorization': 'Basic dGVzdEBleGFtcGxlLmNvbTp0ZXN0'
    })
    token = response.json['token']

    # Отправляем запрос на получение портфеля, передавая токен в заголовке
    response = client.get('/portfolio', headers={
        'Authorization': f'Bearer {token}'
    })

    assert response.status_code == 200
    assert b'[]' in response.data  # Портфель пустой при создании нового пользователя