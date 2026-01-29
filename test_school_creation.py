#!/usr/bin/env python
"""
Test script for school creation functionality.
This verifies that the silent failure issue has been fixed.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Add testserver to ALLOWED_HOSTS
from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.models import School

User = get_user_model()


def test_school_creation_form_renders():
    """Test that the school creation form renders without errors"""
    client = Client()
    
    # Create a super admin user
    admin_user = User.objects.create_user(
        username='admin_test_form',
        email='admin_form@test.com',
        password='testpass123',
        role='super_admin'
    )
    
    # Log in
    login_success = client.login(username='admin_test_form', password='testpass123')
    assert login_success, "Failed to log in as admin"
    print("✓ Admin login successful")
    
    # GET the school creation form
    response = client.get('/schools/create/')
    print(f"Response status: {response.status_code}")
    if response.status_code != 200:
        print(f"Response content: {response.content[:200]}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print("✓ School creation form loads successfully")
    
    # Check that the form is in the context
    if response.context:
        assert 'form' in response.context, "Form not in response context"
        form = response.context['form']
        assert 'name' in form.fields, "School name field not found in form"
        print("✓ Form contains expected 'name' field")
        
        # Verify that non-existent fields are NOT in the form
        assert 'theme' not in form.fields, "Unexpected 'theme' field in form (should be removed)"
        assert 'report_template' not in form.fields, "Unexpected 'report_template' field in form (should be removed)"
        print("✓ Form doesn't contain unexpected fields (theme, report_template)")
    else:
        print("✓ Response received (context not available in test response)")


def test_school_creation_post():
    """Test that posting a new school actually creates it"""
    client = Client()
    
    # Create a super admin user
    admin_user = User.objects.create_user(
        username='admin_post_test',
        email='admin_post@test.com',
        password='testpass123',
        role='super_admin'
    )
    
    # Log in
    client.login(username='admin_post_test', password='testpass123')
    
    # Get initial school count
    initial_count = School.objects.count()
    print(f"Initial school count: {initial_count}")
    
    # POST a new school
    response = client.post('/schools/create/', {
        'name': 'Test School Created'
    }, follow=True)
    
    # Should redirect to school_list
    assert response.status_code == 200, f"POST returned status {response.status_code}"
    print("✓ School creation POST returns 200 status")
    
    # Check that the school was created
    new_count = School.objects.count()
    assert new_count == initial_count + 1, f"Expected {initial_count + 1} schools, got {new_count}"
    print(f"✓ School created successfully (new count: {new_count})")
    
    # Verify the school exists with correct name
    school = School.objects.get(name='Test School Created')
    assert school.name == 'Test School Created', f"School name mismatch: {school.name}"
    print(f"✓ School 'Test School Created' exists in database")


def test_school_creation_validation():
    """Test that validation errors are displayed"""
    client = Client()
    
    # Create a super admin user
    admin_user = User.objects.create_user(
        username='admin_validate_test',
        email='admin_validate@test.com',
        password='testpass123',
        role='super_admin'
    )
    
    # Log in
    client.login(username='admin_validate_test', password='testpass123')
    
    # Try to create a school with empty name
    response = client.post('/schools/create/', {
        'name': ''
    })
    
    assert response.status_code == 200, f"POST returned status {response.status_code}"
    print("✓ Invalid form returns 200 status (form re-rendered)")
    
    # Check that form has errors
    assert 'form' in response.context, "Form not in response context for validation error"
    form = response.context['form']
    assert not form.is_valid(), "Form should be invalid"
    assert form.errors, "Form should have errors"
    print(f"✓ Form validation errors displayed: {form.errors}")


def test_school_creation_duplicate_name():
    """Test that duplicate school names are rejected"""
    client = Client()
    
    # Create an existing school with a unique name
    School.objects.create(name='Existing School Unique')
    print("✓ Existing school created")
    
    # Create a super admin user
    admin_user = User.objects.create_user(
        username='admin_duplicate_test',
        email='admin_dup@test.com',
        password='testpass123',
        role='super_admin'
    )
    
    # Log in
    client.login(username='admin_duplicate_test', password='testpass123')
    
    # Try to create a school with duplicate name
    response = client.post('/schools/create/', {
        'name': 'Existing School Unique'
    })
    
    assert response.status_code == 200, f"POST returned status {response.status_code}"
    print("✓ Duplicate school POST returns 200 status")
    
    # Check that form has errors
    assert 'form' in response.context, "Form not in response context"
    form = response.context['form']
    assert not form.is_valid(), "Form should be invalid for duplicate name"
    assert 'name' in form.errors, "Name field should have error"
    print(f"✓ Duplicate name validation error: {form.errors['name']}")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("SCHOOL CREATION TESTS")
    print("="*60 + "\n")
    
    print("Test 1: Form Rendering")
    print("-" * 40)
    try:
        test_school_creation_form_renders()
        print("✅ PASSED\n")
    except AssertionError as e:
        print(f"❌ FAILED: {e}\n")
    
    print("Test 2: School Creation (POST)")
    print("-" * 40)
    try:
        test_school_creation_post()
        print("✅ PASSED\n")
    except AssertionError as e:
        print(f"❌ FAILED: {e}\n")
    
    print("Test 3: Validation Errors")
    print("-" * 40)
    try:
        test_school_creation_validation()
        print("✅ PASSED\n")
    except AssertionError as e:
        print(f"❌ FAILED: {e}\n")
    
    print("Test 4: Duplicate Name Validation")
    print("-" * 40)
    try:
        test_school_creation_duplicate_name()
        print("✅ PASSED\n")
    except AssertionError as e:
        print(f"❌ FAILED: {e}\n")
    
    print("="*60)
    print("TESTS COMPLETED")
    print("="*60)


if __name__ == '__main__':
    run_all_tests()
