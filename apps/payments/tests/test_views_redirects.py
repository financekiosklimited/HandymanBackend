from django.test import TestCase, override_settings


class StripeRedirectViewsTests(TestCase):
    @override_settings(
        STRIPE_CONNECT_REFRESH_DEEP_LINK="handymankiosk://kyc/connect/refresh"
    )
    def test_connect_refresh_redirect_page(self):
        response = self.client.get("/stripe/connect/refresh/")
        body = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Continue Connect Verification", body)
        self.assertIn("handymankiosk://kyc/connect/refresh", body)
        self.assertIn("window.location.href", body)

    @override_settings(
        STRIPE_CONNECT_RETURN_DEEP_LINK="handymankiosk://kyc/connect/return"
    )
    def test_connect_return_redirect_page(self):
        response = self.client.get("/stripe/connect/return/")
        body = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Connect Verification Updated", body)
        self.assertIn("handymankiosk://kyc/connect/return", body)

    @override_settings(
        STRIPE_IDENTITY_RETURN_DEEP_LINK="handymankiosk://kyc/identity/return"
    )
    def test_identity_return_redirect_page(self):
        response = self.client.get("/stripe/identity/return/")
        body = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Identity Verification Updated", body)
        self.assertIn("handymankiosk://kyc/identity/return", body)

    @override_settings(STRIPE_IDENTITY_RETURN_DEEP_LINK="")
    def test_identity_return_without_deep_link(self):
        response = self.client.get("/stripe/identity/return/")
        body = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("No deep link is configured yet", body)
        self.assertNotIn("window.location.href", body)
