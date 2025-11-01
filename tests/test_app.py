"""
Tests for the Mergington High School Activities API

This module contains comprehensive tests for all API endpoints including:
- GET /activities - Retrieve all activities
- POST /activities/{activity_name}/signup - Sign up for activities
- DELETE /activities/{activity_name}/unregister - Unregister from activities
- GET / - Root redirect functionality
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities
import copy


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities data before each test to ensure test isolation"""
    # Store original activities data
    original_activities = copy.deepcopy(activities)
    
    yield
    
    # Restore original activities data after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Test cases for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that the root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Test cases for the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all available activities"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that we get a dictionary of activities
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check that each activity has required fields
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["max_participants"], int)
    
    def test_get_activities_includes_expected_activities(self, client, reset_activities):
        """Test that specific expected activities are included"""
        response = client.get("/activities")
        data = response.json()
        
        # Check for some expected activities
        expected_activities = ["Chess Club", "Programming Class", "Soccer Team"]
        for activity in expected_activities:
            assert activity in data


class TestSignupForActivity:
    """Test cases for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client, reset_activities):
        """Test successful signup for an activity"""
        activity_name = "Chess Club"
        email = "test@mergington.edu"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == f"Signed up {email} for {activity_name}"
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for a non-existent activity returns 404"""
        activity_name = "Nonexistent Activity"
        email = "test@mergington.edu"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test that signing up the same participant twice returns 400"""
        activity_name = "Chess Club"
        email = "test@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert data["detail"] == "Student already signed up for this activity"
    
    def test_signup_with_existing_participant(self, client, reset_activities):
        """Test signup when activity already has participants"""
        activity_name = "Chess Club"  # This activity has existing participants
        email = "newstudent@mergington.edu"
        
        # Get initial participant count
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity_name]["participants"])
        
        # Sign up new participant
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify participant count increased
        final_response = client.get("/activities")
        final_data = final_response.json()
        final_count = len(final_data[activity_name]["participants"])
        assert final_count == initial_count + 1
        assert email in final_data[activity_name]["participants"]


class TestUnregisterFromActivity:
    """Test cases for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_successful(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        activity_name = "Chess Club"
        email = "test@mergington.edu"
        
        # First sign up
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Then unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        data = unregister_response.json()
        assert data["message"] == f"Unregistered {email} from {activity_name}"
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregistration from a non-existent activity returns 404"""
        activity_name = "Nonexistent Activity"
        email = "test@mergington.edu"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_not_registered_participant(self, client, reset_activities):
        """Test unregistering a participant who is not registered returns 400"""
        activity_name = "Chess Club"
        email = "notregistered@mergington.edu"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is not registered for this activity"
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant (from initial data)"""
        activity_name = "Chess Club"
        # Use an existing participant from the initial data
        email = "michael@mergington.edu"  # This should be in Chess Club initially
        
        # Verify the participant is initially there
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        assert email in initial_data[activity_name]["participants"]
        initial_count = len(initial_data[activity_name]["participants"])
        
        # Unregister
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify participant was removed
        final_response = client.get("/activities")
        final_data = final_response.json()
        assert email not in final_data[activity_name]["participants"]
        assert len(final_data[activity_name]["participants"]) == initial_count - 1


class TestFullWorkflow:
    """Integration tests for complete user workflows"""
    
    def test_complete_signup_unregister_workflow(self, client, reset_activities):
        """Test a complete workflow of signup followed by unregister"""
        activity_name = "Programming Class"
        email = "workflow@mergington.edu"
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_participants = initial_data[activity_name]["participants"].copy()
        
        # Step 1: Sign up
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup_response = client.get("/activities")
        after_signup_data = after_signup_response.json()
        assert email in after_signup_data[activity_name]["participants"]
        assert len(after_signup_data[activity_name]["participants"]) == len(initial_participants) + 1
        
        # Step 2: Unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregister
        final_response = client.get("/activities")
        final_data = final_response.json()
        assert email not in final_data[activity_name]["participants"]
        assert final_data[activity_name]["participants"] == initial_participants
    
    def test_multiple_activities_signup(self, client, reset_activities):
        """Test signing up for multiple activities"""
        email = "multisport@mergington.edu"
        activities_to_join = ["Chess Club", "Soccer Team", "Art Workshop"]
        
        for activity_name in activities_to_join:
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify participant is in all activities
        final_response = client.get("/activities")
        final_data = final_response.json()
        
        for activity_name in activities_to_join:
            assert email in final_data[activity_name]["participants"]


class TestDataValidation:
    """Test cases for data validation and edge cases"""
    
    def test_special_characters_in_email(self, client, reset_activities):
        """Test signup with special characters in email (URL encoding behavior)"""
        activity_name = "Chess Club"
        email = "test+special.email@mergington.edu"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify the participant was added correctly
        # Note: The + character gets URL decoded to a space in query parameters
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        expected_email = "test special.email@mergington.edu"  # + becomes space in URL params
        assert expected_email in activities_data[activity_name]["participants"]
    
    def test_activity_name_with_spaces(self, client, reset_activities):
        """Test operations with activity names containing spaces"""
        activity_name = "Programming Class"  # Contains space
        email = "test@mergington.edu"
        
        # Test signup
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200
        
        # Test unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == 200