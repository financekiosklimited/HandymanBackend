"""Public redirect pages for Stripe Connect/Identity mobile return flows."""

import json

from django.conf import settings
from django.http import HttpResponse
from django.utils.html import escape
from django.views import View


def _build_redirect_page(title, description, deep_link):
    """Render a lightweight HTML page that deep-links back to the mobile app."""
    safe_title = escape(title)
    safe_description = escape(description)
    safe_deep_link = escape(deep_link or "")

    if deep_link:
        script = (
            "<script>"
            f"setTimeout(function(){{window.location.href={json.dumps(deep_link)};}},250);"
            "</script>"
        )
        action = (
            f'<a href="{safe_deep_link}" '
            'style="display:inline-block;padding:12px 18px;background:#111827;color:#fff;'
            'border-radius:8px;text-decoration:none;font-weight:600;">Open HandymanKiosk App</a>'
        )
    else:
        script = ""
        action = (
            '<p style="color:#374151;">'
            "No deep link is configured yet. Please open the HandymanKiosk app manually."
            "</p>"
        )

    html = (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{safe_title}</title></head>"
        '<body style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;'
        'background:#f9fafb;margin:0;padding:24px;">'
        '<div style="max-width:560px;margin:48px auto;background:#fff;border:1px solid #e5e7eb;'
        'border-radius:12px;padding:24px;">'
        f'<h1 style="margin:0 0 12px;font-size:24px;color:#111827;">{safe_title}</h1>'
        f'<p style="margin:0 0 20px;color:#4b5563;line-height:1.5;">{safe_description}</p>'
        f"{action}"
        '<p style="margin-top:16px;color:#6b7280;font-size:13px;">'
        "If nothing happens, tap the button above to continue."
        "</p></div>"
        f"{script}</body></html>"
    )
    return html


class StripeConnectRefreshRedirectView(View):
    """Refresh destination page for Stripe Connect onboarding."""

    def get(self, request):
        return HttpResponse(
            _build_redirect_page(
                title="Continue Connect Verification",
                description=(
                    "Your Stripe Connect verification session needs to be refreshed."
                ),
                deep_link=getattr(settings, "STRIPE_CONNECT_REFRESH_DEEP_LINK", ""),
            )
        )


class StripeConnectReturnRedirectView(View):
    """Return destination page after Stripe Connect onboarding."""

    def get(self, request):
        return HttpResponse(
            _build_redirect_page(
                title="Connect Verification Updated",
                description=(
                    "You're almost done. Return to the app to check your latest KYC status."
                ),
                deep_link=getattr(settings, "STRIPE_CONNECT_RETURN_DEEP_LINK", ""),
            )
        )


class StripeIdentityReturnRedirectView(View):
    """Return destination page after Stripe Identity verification flow."""

    def get(self, request):
        return HttpResponse(
            _build_redirect_page(
                title="Identity Verification Updated",
                description=(
                    "Return to the app to review your Stripe Identity verification result."
                ),
                deep_link=getattr(settings, "STRIPE_IDENTITY_RETURN_DEEP_LINK", ""),
            )
        )
