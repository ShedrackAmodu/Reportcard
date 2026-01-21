import os
import django
from django.test import Client
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

User = get_user_model()

def test_super_admin_api():
    try:
        client = Client()
        print('Client created')

        # Get token
        response = client.post('/api/token/', {'username': 'admin', 'password': 'admin123'}, content_type='application/json')
        print('Token response status:', response.status_code)
        print('Token response content:', response.content.decode()[:500])
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data['access']
            print('Got access token')

            # Test schools endpoint
            headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}
            response = client.get('/api/schools/', **headers)
            print('Schools GET status:', response.status_code)
            if response.status_code == 200:
                print('Schools data:', response.json())

            # Create a school
            response = client.post('/api/schools/', {'name': 'New School', 'theme': {'color': 'blue'}, 'report_template': {}}, content_type='application/json', **headers)
            print('School POST status:', response.status_code)
            if response.status_code == 201:
                print('Created school:', response.json())

            # Test users endpoint
            response = client.get('/api/users/', **headers)
            print('Users GET status:', response.status_code)
            if response.status_code == 200:
                print('Users count:', len(response.json()))

        else:
            print('Token failed')
    except Exception as e:
        print('Error:', e)

if __name__ == '__main__':
    test_super_admin_api()
