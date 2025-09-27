"""
Email service for sending various types of emails.
"""

from django.conf import settings
from django.core.mail import send_mail


class EmailService:
    """
    Service for sending emails.
    """

    def __init__(self):
        self.from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")

    def send_email_verification(self, user, otp_code):
        """
        Send email verification OTP to user.

        Args:
            user: User instance
            otp_code: 6-digit OTP code
        """
        subject = "Verify Your Email Address"
        message = f"""Hi {user.email},

Please verify your email address by entering this code:

{otp_code}

This code will expire in 24 hours.

If you didn't request this, please ignore this email.

Thanks,
The SolutionBank Team"""

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self.from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            # Log the error in a real application
            print(f"Failed to send email verification: {e}")
            return False

    def send_password_reset_code(self, user, reset_code):
        """
        Send password reset code to user.

        Args:
            user: User instance
            reset_code: 6-digit reset code
        """
        subject = "Password Reset Code"
        message = f"""Hi {user.email},

You requested a password reset. Please enter this code to continue:

{reset_code}

This code will expire in 10 minutes.

If you didn't request this, please ignore this email.

Thanks,
The SolutionBank Team"""

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self.from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            # Log the error in a real application
            print(f"Failed to send password reset code: {e}")
            return False

    def send_welcome_email(self, user):
        """
        Send welcome email to new user.

        Args:
            user: User instance
        """
        subject = "Welcome to SB!"
        message = f"""Hi {user.email},

Welcome to SB! We're excited to have you on board.

You can now log in to your account and start using our platform.

Thanks,
The SolutionBank Team"""

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=self.from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            # Log the error in a real application
            print(f"Failed to send welcome email: {e}")
            return False


# Global email service instance
email_service = EmailService()
