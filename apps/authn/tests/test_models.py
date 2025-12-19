"""Tests for authn models."""

import hashlib
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.authn.models import (
    EmailVerificationToken,
    PasswordResetCode,
    PasswordResetToken,
    PhoneVerificationCode,
    RefreshSession,
)


class EmailVerificationTokenModelTests(TestCase):
    """Test cases for EmailVerificationToken model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_create_token_for_user(self):
        """Test creating a verification token for user."""
        token, otp = EmailVerificationToken.create_for_user(self.user)

        self.assertEqual(token.user, self.user)
        self.assertIsNotNone(token.token_hash)
        self.assertIsNotNone(token.expires_at)
        self.assertIsNone(token.used_at)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

    def test_token_hash_matches_otp(self):
        """Test that token hash matches the OTP."""
        token, otp = EmailVerificationToken.create_for_user(self.user)
        expected_hash = hashlib.sha256(otp.encode()).hexdigest()

        self.assertEqual(token.token_hash, expected_hash)

    def test_verify_otp_success(self):
        """Test verifying OTP successfully."""
        token, otp = EmailVerificationToken.create_for_user(self.user)

        verified_user = EmailVerificationToken.verify_otp(self.user.email, otp)

        self.assertEqual(verified_user, self.user)
        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

    def test_verify_otp_invalid_email(self):
        """Test verifying OTP with invalid email."""
        token, otp = EmailVerificationToken.create_for_user(self.user)

        verified_user = EmailVerificationToken.verify_otp("wrong@example.com", otp)

        self.assertIsNone(verified_user)

    def test_verify_otp_invalid_code(self):
        """Test verifying OTP with invalid code."""
        token, otp = EmailVerificationToken.create_for_user(self.user)

        verified_user = EmailVerificationToken.verify_otp(self.user.email, "000000")

        self.assertIsNone(verified_user)

    def test_verify_otp_expired_token(self):
        """Test verifying OTP with expired token."""
        token, otp = EmailVerificationToken.create_for_user(self.user)

        # Manually expire the token
        token.expires_at = timezone.now() - timedelta(hours=1)
        token.save()

        verified_user = EmailVerificationToken.verify_otp(self.user.email, otp)

        self.assertIsNone(verified_user)

    def test_verify_otp_already_used(self):
        """Test verifying OTP that was already used."""
        token, otp = EmailVerificationToken.create_for_user(self.user)

        # Use the token once
        EmailVerificationToken.verify_otp(self.user.email, otp)

        # Try to use it again
        verified_user = EmailVerificationToken.verify_otp(self.user.email, otp)

        self.assertIsNone(verified_user)

    def test_is_valid_method(self):
        """Test is_valid method."""
        token, otp = EmailVerificationToken.create_for_user(self.user)

        self.assertTrue(token.is_valid())

        # Mark as used
        token.used_at = timezone.now()
        token.save()

        self.assertFalse(token.is_valid())

    def test_custom_ttl(self):
        """Test creating token with custom TTL."""
        token, otp = EmailVerificationToken.create_for_user(self.user, ttl_hours=48)

        expected_expiry = timezone.now() + timedelta(hours=48)
        # Allow 1 second tolerance
        self.assertAlmostEqual(
            token.expires_at.timestamp(), expected_expiry.timestamp(), delta=1
        )


class PasswordResetCodeModelTests(TestCase):
    """Test cases for PasswordResetCode model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_create_code_for_user(self):
        """Test creating a reset code for user."""
        code, otp = PasswordResetCode.create_for_user(self.user)

        self.assertEqual(code.user, self.user)
        self.assertIsNotNone(code.code_hash)
        self.assertIsNotNone(code.expires_at)
        self.assertIsNone(code.verified_at)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

    def test_code_hash_matches_otp(self):
        """Test that code hash matches the OTP."""
        code, otp = PasswordResetCode.create_for_user(self.user)
        expected_hash = hashlib.sha256(otp.encode()).hexdigest()

        self.assertEqual(code.code_hash, expected_hash)

    def test_verify_code_success(self):
        """Test verifying reset code successfully."""
        code, otp = PasswordResetCode.create_for_user(self.user)

        verified_code = PasswordResetCode.verify_code(self.user.email, otp)

        self.assertIsNotNone(verified_code)
        self.assertEqual(verified_code.user, self.user)
        self.assertIsNotNone(verified_code.verified_at)

    def test_verify_code_invalid_email(self):
        """Test verifying code with invalid email."""
        code, otp = PasswordResetCode.create_for_user(self.user)

        verified_code = PasswordResetCode.verify_code("wrong@example.com", otp)

        self.assertIsNone(verified_code)

    def test_verify_code_invalid_otp(self):
        """Test verifying code with invalid OTP."""
        code, otp = PasswordResetCode.create_for_user(self.user)

        verified_code = PasswordResetCode.verify_code(self.user.email, "000000")

        self.assertIsNone(verified_code)

    def test_verify_code_expired(self):
        """Test verifying expired reset code."""
        code, otp = PasswordResetCode.create_for_user(self.user)

        # Manually expire the code
        code.expires_at = timezone.now() - timedelta(minutes=1)
        code.save()

        verified_code = PasswordResetCode.verify_code(self.user.email, otp)

        self.assertIsNone(verified_code)

    def test_verify_code_already_verified(self):
        """Test verifying code that was already verified."""
        code, otp = PasswordResetCode.create_for_user(self.user)

        # Verify once
        PasswordResetCode.verify_code(self.user.email, otp)

        # Try to verify again
        verified_code = PasswordResetCode.verify_code(self.user.email, otp)

        self.assertIsNone(verified_code)

    def test_custom_ttl(self):
        """Test creating code with custom TTL."""
        code, otp = PasswordResetCode.create_for_user(self.user, ttl_minutes=30)

        expected_expiry = timezone.now() + timedelta(minutes=30)
        # Allow 1 second tolerance
        self.assertAlmostEqual(
            code.expires_at.timestamp(), expected_expiry.timestamp(), delta=1
        )


class PasswordResetTokenModelTests(TestCase):
    """Test cases for PasswordResetToken model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_create_token_for_user(self):
        """Test creating a reset token for user."""
        token_obj, token = PasswordResetToken.create_for_user(self.user)

        self.assertEqual(token_obj.user, self.user)
        self.assertIsNotNone(token_obj.token_hash)
        self.assertIsNotNone(token_obj.expires_at)
        self.assertIsNone(token_obj.used_at)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

    def test_token_hash_matches_token(self):
        """Test that token hash matches the token."""
        token_obj, token = PasswordResetToken.create_for_user(self.user)
        expected_hash = hashlib.sha256(token.encode()).hexdigest()

        self.assertEqual(token_obj.token_hash, expected_hash)

    def test_verify_token_success(self):
        """Test verifying reset token successfully."""
        token_obj, token = PasswordResetToken.create_for_user(self.user)

        verified_user = PasswordResetToken.verify_token(token)

        self.assertEqual(verified_user, self.user)
        token_obj.refresh_from_db()
        self.assertIsNotNone(token_obj.used_at)

    def test_verify_token_invalid(self):
        """Test verifying invalid token."""
        token_obj, token = PasswordResetToken.create_for_user(self.user)

        verified_user = PasswordResetToken.verify_token("invalid_token")

        self.assertIsNone(verified_user)

    def test_verify_token_expired(self):
        """Test verifying expired token."""
        token_obj, token = PasswordResetToken.create_for_user(self.user)

        # Manually expire the token
        token_obj.expires_at = timezone.now() - timedelta(minutes=1)
        token_obj.save()

        verified_user = PasswordResetToken.verify_token(token)

        self.assertIsNone(verified_user)

    def test_verify_token_already_used(self):
        """Test verifying token that was already used."""
        token_obj, token = PasswordResetToken.create_for_user(self.user)

        # Use the token once
        PasswordResetToken.verify_token(token)

        # Try to use it again
        verified_user = PasswordResetToken.verify_token(token)

        self.assertIsNone(verified_user)

    def test_custom_ttl(self):
        """Test creating token with custom TTL."""
        token_obj, token = PasswordResetToken.create_for_user(self.user, ttl_minutes=30)

        expected_expiry = timezone.now() + timedelta(minutes=30)
        # Allow 1 second tolerance
        self.assertAlmostEqual(
            token_obj.expires_at.timestamp(), expected_expiry.timestamp(), delta=1
        )


class RefreshSessionModelTests(TestCase):
    """Test cases for RefreshSession model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_create_session(self):
        """Test creating a refresh session."""
        jti = "test-jti-123"
        session = RefreshSession.create_session(
            user=self.user,
            platform="web",
            jti=jti,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )

        self.assertEqual(session.user, self.user)
        self.assertEqual(session.platform, "web")
        self.assertEqual(session.user_agent, "Mozilla/5.0")
        self.assertEqual(session.ip_address, "192.168.1.1")
        self.assertIsNotNone(session.jti_hash)
        self.assertIsNotNone(session.expires_at)
        self.assertIsNone(session.revoked_at)

    def test_jti_hash_matches_jti(self):
        """Test that JTI hash matches the JTI."""
        jti = "test-jti-123"
        session = RefreshSession.create_session(user=self.user, platform="web", jti=jti)

        expected_hash = hashlib.sha256(str(jti).encode()).hexdigest()
        self.assertEqual(session.jti_hash, expected_hash)

    def test_verify_session_success(self):
        """Test verifying session successfully."""
        jti = "test-jti-123"
        session = RefreshSession.create_session(user=self.user, platform="web", jti=jti)

        verified_session = RefreshSession.verify_session(jti, "web")

        self.assertEqual(verified_session, session)
        self.assertEqual(verified_session.user, self.user)

    def test_verify_session_invalid_jti(self):
        """Test verifying session with invalid JTI."""
        jti = "test-jti-123"
        RefreshSession.create_session(user=self.user, platform="web", jti=jti)

        verified_session = RefreshSession.verify_session("wrong-jti", "web")

        self.assertIsNone(verified_session)

    def test_verify_session_wrong_platform(self):
        """Test verifying session with wrong platform."""
        jti = "test-jti-123"
        RefreshSession.create_session(user=self.user, platform="web", jti=jti)

        verified_session = RefreshSession.verify_session(jti, "mobile")

        self.assertIsNone(verified_session)

    def test_verify_session_revoked(self):
        """Test verifying revoked session."""
        jti = "test-jti-123"
        session = RefreshSession.create_session(user=self.user, platform="web", jti=jti)

        session.revoke()

        verified_session = RefreshSession.verify_session(jti, "web")

        self.assertIsNone(verified_session)

    def test_verify_session_expired(self):
        """Test verifying expired session."""
        jti = "test-jti-123"
        session = RefreshSession.create_session(user=self.user, platform="web", jti=jti)

        # Manually expire the session
        session.expires_at = timezone.now() - timedelta(minutes=1)
        session.save()

        verified_session = RefreshSession.verify_session(jti, "web")

        self.assertIsNone(verified_session)

    def test_revoke_session(self):
        """Test revoking a session."""
        jti = "test-jti-123"
        session = RefreshSession.create_session(user=self.user, platform="web", jti=jti)

        self.assertTrue(session.is_active())

        session.revoke()

        self.assertFalse(session.is_active())
        self.assertIsNotNone(session.revoked_at)

    def test_revoke_all_for_user(self):
        """Test revoking all sessions for a user."""
        session1 = RefreshSession.create_session(
            user=self.user, platform="web", jti="jti-1"
        )
        session2 = RefreshSession.create_session(
            user=self.user, platform="mobile", jti="jti-2"
        )

        RefreshSession.revoke_all_for_user(self.user)

        session1.refresh_from_db()
        session2.refresh_from_db()

        self.assertIsNotNone(session1.revoked_at)
        self.assertIsNotNone(session2.revoked_at)

    def test_is_active_method(self):
        """Test is_active method."""
        jti = "test-jti-123"
        session = RefreshSession.create_session(user=self.user, platform="web", jti=jti)

        self.assertTrue(session.is_active())

        # Revoke session
        session.revoke()
        self.assertFalse(session.is_active())

        # Test with expired session
        session2 = RefreshSession.create_session(
            user=self.user, platform="web", jti="jti-2"
        )
        session2.expires_at = timezone.now() - timedelta(minutes=1)
        session2.save()

        self.assertFalse(session2.is_active())

    def test_platform_choices(self):
        """Test platform choices are enforced."""
        for platform in ["admin", "web", "mobile"]:
            session = RefreshSession.create_session(
                user=self.user, platform=platform, jti=f"jti-{platform}"
            )
            self.assertEqual(session.platform, platform)

    def test_user_agent_truncation(self):
        """Test user agent is truncated to 1000 chars."""
        long_user_agent = "A" * 2000
        session = RefreshSession.create_session(
            user=self.user, platform="web", jti="test-jti", user_agent=long_user_agent
        )

        self.assertEqual(len(session.user_agent), 1000)

    def test_custom_ttl(self):
        """Test creating session with custom TTL."""
        session = RefreshSession.create_session(
            user=self.user, platform="web", jti="test-jti", ttl_minutes=60
        )

        expected_expiry = timezone.now() + timedelta(minutes=60)
        # Allow 1 second tolerance
        self.assertAlmostEqual(
            session.expires_at.timestamp(), expected_expiry.timestamp(), delta=1
        )

    def test_session_ordering(self):
        """Test sessions are ordered by created_at descending."""
        session1 = RefreshSession.create_session(
            user=self.user, platform="web", jti="jti-1"
        )
        session2 = RefreshSession.create_session(
            user=self.user, platform="web", jti="jti-2"
        )

        sessions = RefreshSession.objects.all()
        self.assertEqual(sessions[0], session2)
        self.assertEqual(sessions[1], session1)

    def test_session_cascade_delete(self):
        """Test session is deleted when user is deleted."""
        session = RefreshSession.create_session(
            user=self.user, platform="web", jti="test-jti"
        )
        session_id = session.id

        self.user.delete()

        self.assertFalse(RefreshSession.objects.filter(id=session_id).exists())


class PhoneVerificationCodeModelTests(TestCase):
    """Test cases for PhoneVerificationCode model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.phone_number = "+16475551234"

    def test_create_for_user(self):
        """Test creating a verification code for user."""
        code, otp = PhoneVerificationCode.create_for_user(self.user, self.phone_number)

        self.assertEqual(code.user, self.user)
        self.assertEqual(code.phone_number, self.phone_number)
        self.assertIsNotNone(code.code_hash)
        self.assertIsNotNone(code.expires_at)
        self.assertIsNone(code.used_at)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

    def test_code_hash_matches_otp(self):
        """Test that code hash matches the OTP."""
        code, otp = PhoneVerificationCode.create_for_user(self.user, self.phone_number)
        expected_hash = hashlib.sha256(otp.encode()).hexdigest()

        self.assertEqual(code.code_hash, expected_hash)

    def test_verify_code_success(self):
        """Test verifying code successfully."""
        code, otp = PhoneVerificationCode.create_for_user(self.user, self.phone_number)

        verified_code = PhoneVerificationCode.verify_code(
            self.user, self.phone_number, otp
        )

        self.assertIsNotNone(verified_code)
        self.assertEqual(verified_code.user, self.user)
        self.assertIsNotNone(verified_code.used_at)

    def test_verify_code_invalid_otp(self):
        """Test verifying code with invalid OTP."""
        code, otp = PhoneVerificationCode.create_for_user(self.user, self.phone_number)

        verified_code = PhoneVerificationCode.verify_code(
            self.user, self.phone_number, "000000"
        )

        self.assertIsNone(verified_code)

    def test_verify_code_expired(self):
        """Test verifying expired code."""
        code, otp = PhoneVerificationCode.create_for_user(self.user, self.phone_number)

        # Manually expire the code
        code.expires_at = timezone.now() - timedelta(minutes=1)
        code.save()

        verified_code = PhoneVerificationCode.verify_code(
            self.user, self.phone_number, otp
        )

        self.assertIsNone(verified_code)

    def test_verify_code_already_used(self):
        """Test verifying code that was already used."""
        code, otp = PhoneVerificationCode.create_for_user(self.user, self.phone_number)

        # Verify once
        PhoneVerificationCode.verify_code(self.user, self.phone_number, otp)

        # Try to verify again
        verified_code = PhoneVerificationCode.verify_code(
            self.user, self.phone_number, otp
        )

        self.assertIsNone(verified_code)

    def test_is_valid_method(self):
        """Test is_valid method."""
        code, otp = PhoneVerificationCode.create_for_user(self.user, self.phone_number)

        self.assertTrue(code.is_valid())

        # Mark as used
        code.used_at = timezone.now()
        code.save()

        self.assertFalse(code.is_valid())

        # Test with expired code
        code2, otp2 = PhoneVerificationCode.create_for_user(
            self.user, self.phone_number
        )
        code2.expires_at = timezone.now() - timedelta(minutes=1)
        code2.save()

        self.assertFalse(code2.is_valid())
