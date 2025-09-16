#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Creator Subscription Platform
Tests all endpoints: auth, creators, content, payments, webhooks
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class CreatorPlatformTester:
    def __init__(self, base_url: str = "https://submaker.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.token = None
        self.user_data = None
        self.creator_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    files: Optional[Dict] = None, expected_status: int = 200) -> tuple[bool, Dict]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                if files:
                    # Remove Content-Type for multipart/form-data
                    headers.pop('Content-Type', None)
                    response = requests.post(url, data=data, files=files, headers=headers)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}
            
            if not success:
                response_data["status_code"] = response.status_code
                
            return success, response_data
            
        except Exception as e:
            return False, {"error": str(e)}

    def test_health_check(self):
        """Test if backend is accessible"""
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            success = response.status_code == 200
            self.log_test("Backend Health Check", success, 
                         f"Status: {response.status_code}" if not success else "")
            return success
        except Exception as e:
            self.log_test("Backend Health Check", False, str(e))
            return False

    def test_user_registration(self):
        """Test user registration endpoint"""
        timestamp = int(time.time())
        test_user = {
            "email": f"testuser{timestamp}@example.com",
            "username": f"testuser{timestamp}",
            "full_name": "Test User",
            "password": "TestPassword123!",
            "is_creator": False
        }
        
        success, response = self.make_request('POST', '/auth/register', test_user, expected_status=200)
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response['user']
            self.log_test("User Registration", True)
            return True
        else:
            self.log_test("User Registration", False, str(response))
            return False

    def test_creator_registration(self):
        """Test creator registration endpoint"""
        timestamp = int(time.time())
        test_creator = {
            "email": f"creator{timestamp}@example.com",
            "username": f"creator{timestamp}",
            "full_name": "Test Creator",
            "password": "TestPassword123!",
            "is_creator": True
        }
        
        success, response = self.make_request('POST', '/auth/register', test_creator, expected_status=200)
        
        if success and 'access_token' in response:
            # Store creator token separately for creator-specific tests
            self.creator_token = response['access_token']
            self.creator_user_data = response['user']
            self.log_test("Creator Registration", True)
            return True
        else:
            self.log_test("Creator Registration", False, str(response))
            return False

    def test_user_login(self):
        """Test user login endpoint"""
        if not self.user_data:
            self.log_test("User Login", False, "No user data available for login test")
            return False
            
        login_data = {
            "email": self.user_data['email'],
            "password": "TestPassword123!"
        }
        
        success, response = self.make_request('POST', '/auth/login', login_data, expected_status=200)
        
        if success and 'access_token' in response:
            self.log_test("User Login", True)
            return True
        else:
            self.log_test("User Login", False, str(response))
            return False

    def test_get_current_user(self):
        """Test get current user endpoint"""
        if not self.token:
            self.log_test("Get Current User", False, "No authentication token available")
            return False
            
        success, response = self.make_request('GET', '/auth/me', expected_status=200)
        
        if success and 'id' in response:
            self.log_test("Get Current User", True)
            return True
        else:
            self.log_test("Get Current User", False, str(response))
            return False

    def test_create_creator_profile(self):
        """Test creator profile creation"""
        if not hasattr(self, 'creator_token'):
            self.log_test("Create Creator Profile", False, "No creator token available")
            return False
            
        # Switch to creator token
        original_token = self.token
        self.token = self.creator_token
        
        creator_profile = {
            "display_name": "Amazing Creator",
            "bio": "I create amazing content for my fans!",
            "category": "lifestyle",
            "tags": ["lifestyle", "motivation", "wellness"],
            "subscription_price": 19.99
        }
        
        success, response = self.make_request('POST', '/creators', creator_profile, expected_status=200)
        
        if success and 'id' in response:
            self.creator_data = response
            self.log_test("Create Creator Profile", True)
            result = True
        else:
            self.log_test("Create Creator Profile", False, str(response))
            result = False
            
        # Restore original token
        self.token = original_token
        return result

    def test_get_creators(self):
        """Test get creators endpoint"""
        success, response = self.make_request('GET', '/creators', expected_status=200)
        
        if success and isinstance(response, list):
            self.log_test("Get Creators", True, f"Found {len(response)} creators")
            return True
        else:
            self.log_test("Get Creators", False, str(response))
            return False

    def test_get_creator_by_id(self):
        """Test get specific creator endpoint"""
        if not self.creator_data:
            self.log_test("Get Creator By ID", False, "No creator data available")
            return False
            
        creator_id = self.creator_data['id']
        success, response = self.make_request('GET', f'/creators/{creator_id}', expected_status=200)
        
        if success and response.get('id') == creator_id:
            self.log_test("Get Creator By ID", True)
            return True
        else:
            self.log_test("Get Creator By ID", False, str(response))
            return False

    def test_create_content(self):
        """Test content creation endpoint"""
        if not hasattr(self, 'creator_token') or not self.creator_data:
            self.log_test("Create Content", False, "No creator token or profile available")
            return False
            
        # Switch to creator token
        original_token = self.token
        self.token = self.creator_token
        
        # Test text content creation
        content_data = {
            "title": "My First Post",
            "description": "This is my first amazing post!",
            "is_premium": False,
            "is_ppv": False,
            "tags": "lifestyle,motivation"
        }
        
        success, response = self.make_request('POST', '/content', content_data, expected_status=200)
        
        if success and 'content_id' in response:
            self.content_id = response['content_id']
            self.log_test("Create Content", True)
            result = True
        else:
            self.log_test("Create Content", False, str(response))
            result = False
            
        # Restore original token
        self.token = original_token
        return result

    def test_get_content(self):
        """Test get content endpoint"""
        success, response = self.make_request('GET', '/content', expected_status=200)
        
        if success and isinstance(response, list):
            self.log_test("Get Content", True, f"Found {len(response)} content items")
            return True
        else:
            self.log_test("Get Content", False, str(response))
            return False

    def test_subscription_payment(self):
        """Test subscription payment endpoint"""
        if not self.token or not self.creator_data:
            self.log_test("Subscription Payment", False, "No user token or creator data available")
            return False
            
        subscription_data = {
            "creator_id": self.creator_data['id'],
            "plan_type": "premium"
        }
        
        success, response = self.make_request('POST', '/payments/subscribe', subscription_data, expected_status=200)
        
        if success and 'checkout_url' in response and 'session_id' in response:
            self.session_id = response['session_id']
            self.log_test("Subscription Payment", True, "Checkout URL generated")
            return True
        else:
            self.log_test("Subscription Payment", False, str(response))
            return False

    def test_tip_payment(self):
        """Test tip payment endpoint"""
        if not self.token or not self.creator_data:
            self.log_test("Tip Payment", False, "No user token or creator data available")
            return False
            
        tip_data = {
            "creator_id": self.creator_data['id'],
            "amount": 5.0,
            "message": "Great content!"
        }
        
        success, response = self.make_request('POST', '/payments/tip', tip_data, expected_status=200)
        
        if success and 'checkout_url' in response and 'session_id' in response:
            self.log_test("Tip Payment", True, "Checkout URL generated")
            return True
        else:
            self.log_test("Tip Payment", False, str(response))
            return False

    def test_payment_status(self):
        """Test payment status endpoint"""
        if not hasattr(self, 'session_id'):
            self.log_test("Payment Status", False, "No session ID available")
            return False
            
        success, response = self.make_request('GET', f'/payments/status/{self.session_id}', expected_status=200)
        
        if success and 'payment_status' in response:
            self.log_test("Payment Status", True, f"Status: {response['payment_status']}")
            return True
        else:
            self.log_test("Payment Status", False, str(response))
            return False

    def test_creator_stats(self):
        """Test creator dashboard stats endpoint"""
        if not hasattr(self, 'creator_token'):
            self.log_test("Creator Stats", False, "No creator token available")
            return False
            
        # Switch to creator token
        original_token = self.token
        self.token = self.creator_token
        
        success, response = self.make_request('GET', '/dashboard/creator/stats', expected_status=200)
        
        if success and 'subscriber_count' in response:
            self.log_test("Creator Stats", True, f"Stats retrieved: {response}")
            result = True
        else:
            self.log_test("Creator Stats", False, str(response))
            result = False
            
        # Restore original token
        self.token = original_token
        return result

    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting Creator Platform Backend API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Health check first
        if not self.test_health_check():
            print("❌ Backend is not accessible. Stopping tests.")
            return False
        
        # Authentication tests
        print("\n📝 Testing Authentication...")
        self.test_user_registration()
        self.test_creator_registration()
        self.test_user_login()
        self.test_get_current_user()
        
        # Creator management tests
        print("\n👤 Testing Creator Management...")
        self.test_create_creator_profile()
        self.test_get_creators()
        self.test_get_creator_by_id()
        
        # Content management tests
        print("\n📄 Testing Content Management...")
        self.test_create_content()
        self.test_get_content()
        
        # Payment tests
        print("\n💳 Testing Payment System...")
        self.test_subscription_payment()
        self.test_tip_payment()
        self.test_payment_status()
        
        # Dashboard tests
        print("\n📊 Testing Dashboard...")
        self.test_creator_stats()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['name']}: {result['details']}")
            return False

def main():
    """Main test execution"""
    tester = CreatorPlatformTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())