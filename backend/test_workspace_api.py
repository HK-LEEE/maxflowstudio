#!/usr/bin/env python3
"""Test workspace API endpoint"""

from fastapi.testclient import TestClient
from src.main import app

def test_workspace_api():
    # Create test client
    client = TestClient(app)
    
    # Mock the get_current_user dependency
    def mock_current_user():
        from src.models.user import User
        return User(
            id='21a2aaa7-444a-4038-bda3-d8bf2c4ef162',
            username='admin',
            email='admin@test.com',
            is_active=True,
            is_superuser=True
        )
    
    # Override the dependency
    from src.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = mock_current_user
    
    try:
        # Test workspace creation
        print("Testing workspace creation API...")
        response = client.post('/api/workspaces/', json={
            'name': 'API Test Workspace',
            'type': 'user'
        })
        
        print(f'Response status: {response.status_code}')
        print(f'Response headers: {dict(response.headers)}')
        print(f'Response content: {response.text}')
        
        if response.status_code != 200:
            try:
                error_detail = response.json()
                print(f'ERROR JSON: {error_detail}')
            except:
                print(f'ERROR TEXT: {response.text}')
        else:
            print('SUCCESS: Workspace created via API')
            data = response.json()
            print(f'Created workspace: {data}')
            
    except Exception as e:
        print(f'Exception during API test: {e}')
        import traceback
        traceback.print_exc()
    finally:
        # Clean up override
        app.dependency_overrides.clear()

if __name__ == "__main__":
    test_workspace_api()