"""
Authentication System Tests for Fractured Survival NPC Service
Tests: Registration, Login, Token Verification, User Info, Unreal Engine Connect
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthRegistration:
    """User registration endpoint tests"""
    
    def test_register_new_user_success(self):
        """Test successful user registration"""
        unique_username = f"TEST_user_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": unique_username,
            "password": "testpass123",
            "email": f"{unique_username}@test.com",
            "player_name": f"Player_{unique_username[:8]}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "user_id" in data
        assert "token" in data
        assert data["username"] == unique_username
        assert data["auth_source"] == "web"
    
    def test_register_without_email(self):
        """Test registration without optional email"""
        unique_username = f"TEST_noemail_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": unique_username,
            "password": "testpass123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["player_name"] == unique_username  # Defaults to username
    
    def test_register_duplicate_username(self):
        """Test registration with existing username fails"""
        # First registration
        unique_username = f"TEST_dup_{uuid.uuid4().hex[:8]}"
        requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": unique_username,
            "password": "testpass123"
        })
        
        # Second registration with same username
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": unique_username,
            "password": "differentpass"
        })
        
        assert response.status_code == 400
        assert "already exists" in response.json().get("detail", "").lower()


class TestAuthLogin:
    """User login endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup_test_user(self):
        """Create a test user for login tests"""
        self.test_username = f"TEST_login_{uuid.uuid4().hex[:8]}"
        self.test_password = "logintest123"
        
        requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": self.test_username,
            "password": self.test_password,
            "player_name": "LoginTestPlayer"
        })
    
    def test_login_success(self):
        """Test successful login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": self.test_username,
            "password": self.test_password
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "token" in data
        assert "user_id" in data
        assert data["username"] == self.test_username
    
    def test_login_invalid_password(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": self.test_username,
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "invalid" in response.json().get("detail", "").lower()
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "nonexistent_user_xyz",
            "password": "anypassword"
        })
        
        assert response.status_code == 401


class TestTokenVerification:
    """Token verification endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get a valid auth token"""
        unique_username = f"TEST_verify_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": unique_username,
            "password": "verifytest123"
        })
        return response.json().get("token")
    
    def test_verify_valid_token(self, auth_token):
        """Test verification of valid token"""
        response = requests.post(f"{BASE_URL}/api/auth/verify", headers={
            "Authorization": f"Bearer {auth_token}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert "user_id" in data
        assert "username" in data
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        response = requests.post(f"{BASE_URL}/api/auth/verify", headers={
            "Authorization": "Bearer invalid_token_xyz"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == False
    
    def test_verify_no_token(self):
        """Test verification without token"""
        response = requests.post(f"{BASE_URL}/api/auth/verify")
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == False


class TestGetCurrentUser:
    """Get current user info endpoint tests"""
    
    @pytest.fixture
    def auth_data(self):
        """Create user and get auth data"""
        unique_username = f"TEST_me_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": unique_username,
            "password": "metest123",
            "email": f"{unique_username}@test.com",
            "player_name": "MeTestPlayer"
        })
        return response.json()
    
    def test_get_me_authenticated(self, auth_data):
        """Test getting current user info with valid token"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {auth_data['token']}"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == auth_data["user_id"]
        assert data["username"] == auth_data["username"]
        assert "created_at" in data
        assert "last_login" in data
    
    def test_get_me_unauthenticated(self):
        """Test getting current user info without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 401


class TestUnrealEngineAuth:
    """Unreal Engine authentication endpoint tests"""
    
    def test_unreal_connect_new_player(self):
        """Test Unreal Engine connect creates new player"""
        unique_player_id = f"TEST_unreal_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/auth/unreal/connect", json={
            "unreal_player_id": unique_player_id,
            "player_name": "UnrealTestPlayer"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["is_new"] == True
        assert "token" in data
        assert "generated_password" in data  # New users get generated password
        assert data["username"] == unique_player_id
    
    def test_unreal_connect_existing_player(self):
        """Test Unreal Engine connect returns existing player"""
        unique_player_id = f"TEST_unreal_exist_{uuid.uuid4().hex[:8]}"
        
        # First connect - creates user
        first_response = requests.post(f"{BASE_URL}/api/auth/unreal/connect", json={
            "unreal_player_id": unique_player_id,
            "player_name": "ExistingPlayer"
        })
        first_user_id = first_response.json()["user_id"]
        
        # Second connect - returns existing
        second_response = requests.post(f"{BASE_URL}/api/auth/unreal/connect", json={
            "unreal_player_id": unique_player_id
        })
        
        assert second_response.status_code == 200
        data = second_response.json()
        assert data["success"] == True
        assert data["is_new"] == False
        assert data["user_id"] == first_user_id
        assert "generated_password" not in data  # Existing users don't get new password
    
    def test_unreal_connect_with_password(self):
        """Test Unreal Engine connect with provided password"""
        unique_player_id = f"TEST_unreal_pwd_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/auth/unreal/connect", json={
            "unreal_player_id": unique_player_id,
            "player_name": "PasswordPlayer",
            "password": "custom_password_123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "generated_password" not in data  # No generated password when provided


class TestAuthIntegration:
    """Integration tests for auth flow"""
    
    def test_full_auth_flow(self):
        """Test complete auth flow: register -> login -> verify -> me"""
        unique_username = f"TEST_flow_{uuid.uuid4().hex[:8]}"
        
        # 1. Register
        reg_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": unique_username,
            "password": "flowtest123",
            "player_name": "FlowTestPlayer"
        })
        assert reg_response.status_code == 200
        reg_data = reg_response.json()
        assert reg_data["success"] == True
        
        # 2. Login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": unique_username,
            "password": "flowtest123"
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        token = login_data["token"]
        
        # 3. Verify token
        verify_response = requests.post(f"{BASE_URL}/api/auth/verify", headers={
            "Authorization": f"Bearer {token}"
        })
        assert verify_response.status_code == 200
        assert verify_response.json()["valid"] == True
        
        # 4. Get user info
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["username"] == unique_username
        assert me_data["player_name"] == "FlowTestPlayer"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
