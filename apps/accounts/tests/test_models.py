"""
Tests for accounts models.
"""

from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import UserRole

User = get_user_model()


class TestUserManager(TestCase):
    """Test custom UserManager methods."""

    def test_create_user_success(self):
        """Test creating a regular user with email and password."""
        email = "test@example.com"
        password = "testpass123"
        user = User.objects.create_user(email=email, password=password)

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNotNone(user.public_id)

    def test_create_user_normalizes_email(self):
        """Test email is normalized when creating user."""
        email = "test@EXAMPLE.COM"
        user = User.objects.create_user(email=email, password="testpass123")

        self.assertEqual(user.email, "test@example.com")

    def test_create_user_without_email_raises_error(self):
        """Test creating user without email raises ValueError."""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(email="", password="testpass123")

        self.assertIn("Email field must be set", str(context.exception))

    def test_create_user_with_extra_fields(self):
        """Test creating user with extra fields."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )

        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")

    def test_create_superuser_success(self):
        """Test creating a superuser."""
        email = "admin@example.com"
        password = "adminpass123"
        user = User.objects.create_superuser(email=email, password=password)

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_with_is_staff_false_raises_error(self):
        """Test creating superuser with is_staff=False raises ValueError."""
        with self.assertRaises(ValueError) as context:
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass123", is_staff=False
            )

        self.assertIn("Superuser must have is_staff=True", str(context.exception))

    def test_create_superuser_with_is_superuser_false_raises_error(self):
        """Test creating superuser with is_superuser=False raises ValueError."""
        with self.assertRaises(ValueError) as context:
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass123", is_superuser=False
            )

        self.assertIn("Superuser must have is_superuser=True", str(context.exception))


class TestUserModel(TestCase):
    """Test User model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_user_str_returns_email(self):
        """Test string representation returns email."""
        self.assertEqual(str(self.user), "test@example.com")

    def test_email_is_unique(self):
        """Test email uniqueness constraint."""
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="test@example.com", password="anotherpass123"
            )

    def test_public_id_is_auto_generated(self):
        """Test public_id is automatically generated."""
        self.assertIsNotNone(self.user.public_id)

    def test_public_id_is_unique(self):
        """Test public_id is unique across users."""
        user2 = User.objects.create_user(
            email="test2@example.com", password="testpass123"
        )

        self.assertNotEqual(self.user.public_id, user2.public_id)

    def test_save_regenerates_public_id_when_missing(self):
        """Test save assigns a new public_id if it was cleared manually."""
        original = self.user.public_id
        self.user.public_id = None
        self.user.save()
        self.user.refresh_from_db()

        self.assertIsNotNone(self.user.public_id)
        self.assertNotEqual(self.user.public_id, original)

    def test_timestamps_are_auto_generated(self):
        """Test created_at and updated_at are automatically set."""
        self.assertIsNotNone(self.user.created_at)
        self.assertIsNotNone(self.user.updated_at)

    def test_is_email_verified_property_false_by_default(self):
        """Test is_email_verified returns False when email_verified_at is None."""
        self.assertFalse(self.user.is_email_verified)

    def test_is_email_verified_property_true_when_verified(self):
        """Test is_email_verified returns True when email_verified_at is set."""
        self.user.email_verified_at = timezone.now()
        self.user.save()

        self.assertTrue(self.user.is_email_verified)

    def test_google_sub_is_unique(self):
        """Test google_sub uniqueness constraint."""
        self.user.google_sub = "google123"
        self.user.save()

        user2 = User.objects.create_user(
            email="test2@example.com", password="testpass123"
        )

        with self.assertRaises(IntegrityError):
            user2.google_sub = "google123"
            user2.save()

    def test_google_sub_can_be_null(self):
        """Test google_sub can be null for multiple users."""
        user2 = User.objects.create_user(
            email="test2@example.com", password="testpass123"
        )

        self.assertIsNone(self.user.google_sub)
        self.assertIsNone(user2.google_sub)

    def test_user_ordering_by_created_at_desc(self):
        """Test users are ordered by created_at descending."""
        user2 = User.objects.create_user(
            email="test2@example.com", password="testpass123"
        )

        users = User.objects.all()
        self.assertEqual(users[0], user2)  # Most recent first
        self.assertEqual(users[1], self.user)

    def test_has_role_returns_true_when_role_exists(self):
        """Test has_role returns True when user has the role."""
        UserRole.objects.create(user=self.user, role="homeowner")

        self.assertTrue(self.user.has_role("homeowner"))

    def test_has_role_returns_false_when_role_does_not_exist(self):
        """Test has_role returns False when user doesn't have the role."""
        self.assertFalse(self.user.has_role("homeowner"))

    def test_get_role_returns_role_when_exists(self):
        """Test get_role returns UserRole instance when role exists."""
        role = UserRole.objects.create(user=self.user, role="handyman")

        retrieved_role = self.user.get_role("handyman")
        self.assertEqual(retrieved_role, role)

    def test_get_role_returns_none_when_not_exists(self):
        """Test get_role returns None when role doesn't exist."""
        retrieved_role = self.user.get_role("admin")

        self.assertIsNone(retrieved_role)


class TestUserRoleModel(TestCase):
    """Test UserRole model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_create_user_role_success(self):
        """Test creating a user role."""
        role = UserRole.objects.create(user=self.user, role="homeowner")

        self.assertEqual(role.user, self.user)
        self.assertEqual(role.role, "homeowner")
        self.assertEqual(role.next_action, "verify_email")  # Default value
        self.assertIsNotNone(role.public_id)
        self.assertIsNotNone(role.created_at)

    def test_user_role_str_representation(self):
        """Test string representation of UserRole."""
        role = UserRole.objects.create(user=self.user, role="handyman")

        self.assertEqual(str(role), "test@example.com - handyman")

    def test_role_choices_are_valid(self):
        """Test all role choices can be created."""
        for role_value, _ in UserRole.ROLE_CHOICES:
            user_role = UserRole.objects.create(user=self.user, role=role_value)
            self.assertEqual(user_role.role, role_value)
            # Clean up for next iteration
            user_role.delete()

    def test_next_action_choices_are_valid(self):
        """Test all next_action choices can be set."""
        role = UserRole.objects.create(user=self.user, role="homeowner")

        for action_value, _ in UserRole.NEXT_ACTION_CHOICES:
            role.next_action = action_value
            role.save()
            role.refresh_from_db()
            self.assertEqual(role.next_action, action_value)

    def test_unique_together_constraint(self):
        """Test user-role combination is unique."""
        UserRole.objects.create(user=self.user, role="homeowner")

        with self.assertRaises(IntegrityError):
            UserRole.objects.create(user=self.user, role="homeowner")

    def test_user_can_have_multiple_roles(self):
        """Test user can have multiple different roles."""
        role1 = UserRole.objects.create(user=self.user, role="homeowner")
        role2 = UserRole.objects.create(user=self.user, role="handyman")

        self.assertEqual(self.user.roles.count(), 2)
        self.assertIn(role1, self.user.roles.all())
        self.assertIn(role2, self.user.roles.all())

    def test_user_role_cascade_delete(self):
        """Test roles are deleted when user is deleted."""
        UserRole.objects.create(user=self.user, role="homeowner")
        UserRole.objects.create(user=self.user, role="handyman")

        user_id = self.user.id
        self.user.delete()

        self.assertEqual(UserRole.objects.filter(user_id=user_id).count(), 0)

    def test_user_role_ordering_by_created_at_desc(self):
        """Test user roles are ordered by created_at descending."""
        role1 = UserRole.objects.create(user=self.user, role="homeowner")
        role2 = UserRole.objects.create(user=self.user, role="handyman")

        roles = UserRole.objects.all()
        self.assertEqual(roles[0], role2)  # Most recent first
        self.assertEqual(roles[1], role1)

    def test_default_next_action_is_verify_email(self):
        """Test default next_action is 'verify_email'."""
        role = UserRole.objects.create(user=self.user, role="homeowner")

        self.assertEqual(role.next_action, "verify_email")

    def test_custom_next_action_can_be_set(self):
        """Test custom next_action can be set on creation."""
        role = UserRole.objects.create(
            user=self.user, role="homeowner", next_action="fill_profile"
        )

        self.assertEqual(role.next_action, "fill_profile")
