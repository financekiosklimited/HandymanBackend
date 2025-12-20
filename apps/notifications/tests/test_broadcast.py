"""Tests for broadcast notifications."""

from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User, UserRole
from apps.notifications.models import BroadcastNotification, Notification, UserDevice
from apps.notifications.services import NotificationService


class BroadcastNotificationTests(TestCase):
    """Test cases for BroadcastNotification."""

    def setUp(self):
        self.service = NotificationService()
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="password123"
        )

        # Create some users with different roles
        self.handyman = User.objects.create_user(
            email="handyman@example.com", password="password123"
        )
        UserRole.objects.create(user=self.handyman, role="handyman")

        self.homeowner = User.objects.create_user(
            email="homeowner@example.com", password="password123"
        )
        UserRole.objects.create(user=self.homeowner, role="homeowner")

        self.both = User.objects.create_user(
            email="both@example.com", password="password123"
        )
        UserRole.objects.create(user=self.both, role="handyman")
        UserRole.objects.create(user=self.both, role="homeowner")

    def test_get_target_users_all(self):
        """Test getting all users for broadcast."""
        users = self.service.get_target_users("all")
        # admin, handyman, homeowner, both = 4 users
        self.assertEqual(users.count(), 4)

    def test_get_target_users_handyman(self):
        """Test getting only handyman users."""
        users = self.service.get_target_users("handyman")
        # handyman, both = 2 users
        self.assertEqual(users.count(), 2)
        self.assertTrue(users.filter(email=self.handyman.email).exists())
        self.assertTrue(users.filter(email=self.both.email).exists())

    def test_get_target_users_homeowner(self):
        """Test getting only homeowner users."""
        users = self.service.get_target_users("homeowner")
        # homeowner, both = 2 users
        self.assertEqual(users.count(), 2)
        self.assertTrue(users.filter(email=self.homeowner.email).exists())
        self.assertTrue(users.filter(email=self.both.email).exists())

    def test_get_target_users_specific(self):
        """Test getting specific users only."""
        broadcast = BroadcastNotification.objects.create(
            title="Specific",
            body="Body",
            target_audience="specific",
            sent_by=self.admin,
        )
        broadcast.target_users.add(self.handyman, self.homeowner)

        users = self.service.get_target_users("specific", broadcast)
        self.assertEqual(users.count(), 2)
        self.assertTrue(users.filter(email=self.handyman.email).exists())
        self.assertTrue(users.filter(email=self.homeowner.email).exists())

    @patch("apps.notifications.services.firebase_service")
    def test_send_broadcast_all(self, mock_firebase):
        """Test sending broadcast to all users."""
        broadcast = BroadcastNotification.objects.create(
            title="Broadcast Title",
            body="Broadcast Body",
            target_audience="all",
            sent_by=self.admin,
            send_push=True,
        )

        # Create devices for some users
        UserDevice.objects.create(
            user=self.handyman, device_token="h_token", device_type="android"
        )
        UserDevice.objects.create(
            user=self.homeowner, device_token="o_token", device_type="ios"
        )

        mock_firebase.send_multicast_notification.return_value = {
            "success_count": 2,
            "failure_count": 0,
        }

        self.service.send_broadcast(broadcast)

        # Verify status and stats
        broadcast.refresh_from_db()
        self.assertEqual(broadcast.status, "completed")
        self.assertEqual(broadcast.total_recipients, 4)
        self.assertEqual(broadcast.push_success_count, 2)

        # Verify in-app notifications created
        self.assertEqual(
            Notification.objects.filter(title="Broadcast Title").count(), 4
        )

        # Verify Firebase called
        self.assertTrue(mock_firebase.send_multicast_notification.called)

    @patch("apps.notifications.services.firebase_service")
    def test_send_broadcast_specific(self, mock_firebase):
        """Test sending broadcast to specific users only."""
        broadcast = BroadcastNotification.objects.create(
            title="Specific Title",
            body="Specific Body",
            target_audience="specific",
            sent_by=self.admin,
            send_push=True,
        )
        broadcast.target_users.add(self.handyman, self.homeowner)

        UserDevice.objects.create(
            user=self.handyman, device_token="h_token", device_type="android"
        )
        UserDevice.objects.create(
            user=self.homeowner, device_token="o_token", device_type="ios"
        )

        mock_firebase.send_multicast_notification.return_value = {
            "success_count": 2,
            "failure_count": 0,
        }

        self.service.send_broadcast(broadcast)

        broadcast.refresh_from_db()
        self.assertEqual(broadcast.status, "completed")
        self.assertEqual(broadcast.total_recipients, 2)
        self.assertEqual(broadcast.push_success_count, 2)
        self.assertEqual(Notification.objects.filter(title="Specific Title").count(), 2)
        self.assertTrue(mock_firebase.send_multicast_notification.called)

    def test_send_broadcast_specific_without_users_raises(self):
        """Specific target requires at least one user."""
        broadcast = BroadcastNotification.objects.create(
            title="No Users",
            body="Body",
            target_audience="specific",
            sent_by=self.admin,
            send_push=False,
        )

        with self.assertRaises(ValueError):
            self.service.send_broadcast(broadcast)

    @patch("apps.notifications.services.firebase_service")
    def test_send_broadcast_no_push(self, mock_firebase):
        """Test sending broadcast without push notification."""
        broadcast = BroadcastNotification.objects.create(
            title="No Push",
            body="Body",
            target_audience="handyman",
            sent_by=self.admin,
            send_push=False,
        )

        self.service.send_broadcast(broadcast)

        broadcast.refresh_from_db()
        self.assertEqual(broadcast.total_recipients, 2)
        self.assertEqual(broadcast.push_success_count, 0)

        # Verify in-app notifications created
        self.assertEqual(Notification.objects.filter(title="No Push").count(), 2)

        # Verify Firebase NOT called
        mock_firebase.send_multicast_notification.assert_not_called()
