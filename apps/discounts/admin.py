"""
Admin configuration for Discounts app using Django Unfold.
"""

from django import forms
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Discount, UserDiscountUsage


class UserDiscountUsageInline(admin.TabularInline):
    """Inline display of discount usages in Discount admin."""

    model = UserDiscountUsage
    extra = 0
    readonly_fields = ["user", "job", "used_at", "usage_number"]
    can_delete = False
    fields = ["user", "job", "used_at", "usage_number"]
    ordering = ["-used_at"]

    def has_add_permission(self, request, obj=None):
        return False


class DiscountForm(forms.ModelForm):
    """Custom form for Discount with validation."""

    class Meta:
        model = Discount
        fields = "__all__"

    def clean_code(self):
        """Ensure code is uppercase."""
        code = self.cleaned_data.get("code", "")
        return code.upper()


@admin.register(Discount)
class DiscountAdmin(ModelAdmin):
    """Admin interface for managing discounts."""

    form = DiscountForm

    # List view configuration
    list_display = [
        "name",
        "code_display",
        "discount_display",
        "target_role_badge",
        "date_range",
        "usage_stats",
        "status_badge",
        "ends_in_display",
    ]

    list_filter = [
        "target_role",
        "discount_type",
        "is_active",
        "start_date",
        "end_date",
    ]

    search_fields = ["name", "code", "description"]
    ordering = ["-created_at"]

    # Detail view configuration
    fieldsets = (
        ("Basic Information", {"fields": ("name", "code", "description", "is_active")}),
        (
            "Terms and Conditions",
            {
                "fields": ("terms_and_conditions",),
                "description": "Terms shown to users. Include disclaimer about app cut fee.",
            },
        ),
        (
            "Discount Details",
            {"fields": ("discount_type", "discount_value", "target_role")},
        ),
        ("Validity Period", {"fields": ("start_date", "end_date")}),
        (
            "Usage Limits",
            {
                "fields": ("max_uses_global", "max_uses_per_user", "total_used_count"),
                "description": "Set max_uses_global to 0 for unlimited total uses.",
            },
        ),
        (
            "Visual Styling",
            {"fields": ("color", "icon", "badge_text"), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["total_used_count", "created_at", "updated_at"]

    # Inlines
    inlines = [UserDiscountUsageInline]

    # Actions
    actions = ["activate_discounts", "deactivate_discounts", "duplicate_discount"]

    @display(description="Code")
    def code_display(self, obj):
        """Display code in monospace."""
        return format_html(
            '<code style="font-size: 1.1em; background: #f5f5f5; padding: 2px 6px; '
            'border-radius: 3px;">{}</code>',
            obj.code,
        )

    @display(description="Discount")
    def discount_display(self, obj):
        """Display formatted discount."""
        return obj.get_discount_display()

    @display(description="Target")
    def target_role_badge(self, obj):
        """Display target role as badge."""
        colors = {
            "homeowner": "green",
            "handyman": "blue",
            "both": "purple",
        }
        color = colors.get(obj.target_role, "gray")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 0.85em;">{}</span>',
            color,
            obj.get_target_role_display(),
        )

    @display(description="Valid Period")
    def date_range(self, obj):
        """Display date range."""
        return f"{obj.start_date.strftime('%Y-%m-%d')} to {obj.end_date.strftime('%Y-%m-%d')}"

    @display(description="Usage")
    def usage_stats(self, obj):
        """Display usage statistics."""
        if obj.max_uses_global == 0:
            return f"{obj.total_used_count} / ∞"
        return f"{obj.total_used_count} / {obj.max_uses_global}"

    @display(description="Status")
    def status_badge(self, obj):
        """Display status badge."""
        if not obj.is_active:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 2px 8px; '
                'border-radius: 12px; font-size: 0.85em;">Inactive</span>'
            )

        now = timezone.now()
        if now < obj.start_date:
            return format_html(
                '<span style="background: #ffc107; color: black; padding: 2px 8px; '
                'border-radius: 12px; font-size: 0.85em;">Upcoming</span>'
            )
        elif now > obj.end_date:
            return format_html(
                '<span style="background: #6c757d; color: white; padding: 2px 8px; '
                'border-radius: 12px; font-size: 0.85em;">Expired</span>'
            )
        else:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 2px 8px; '
                'border-radius: 12px; font-size: 0.85em;">Active</span>'
            )

    @display(description="Expires")
    def ends_in_display(self, obj):
        """Display expiry countdown."""
        return obj.get_expiry_text()

    @admin.action(description="Activate selected discounts")
    def activate_discounts(self, request, queryset):
        """Bulk activate discounts."""
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} discount(s) activated.", messages.SUCCESS)

    @admin.action(description="Deactivate selected discounts")
    def deactivate_discounts(self, request, queryset):
        """Bulk deactivate discounts."""
        count = queryset.update(is_active=False)
        self.message_user(
            request, f"{count} discount(s) deactivated.", messages.SUCCESS
        )

    @admin.action(description="Duplicate selected discount")
    def duplicate_discount(self, request, queryset):
        """Duplicate a discount with new code."""
        if queryset.count() != 1:
            self.message_user(
                request,
                "Please select exactly one discount to duplicate.",
                messages.ERROR,
            )
            return

        original = queryset.first()

        # Create copy with modified name and code
        new_discount = Discount.objects.create(
            name=f"{original.name} (Copy)",
            code=f"{original.code}_COPY",
            description=original.description,
            terms_and_conditions=original.terms_and_conditions,
            discount_type=original.discount_type,
            discount_value=original.discount_value,
            target_role=original.target_role,
            start_date=original.start_date,
            end_date=original.end_date,
            max_uses_global=original.max_uses_global,
            max_uses_per_user=original.max_uses_per_user,
            is_active=False,  # Start inactive so admin can review
            color=original.color,
            icon=original.icon,
            badge_text=original.badge_text,
        )

        self.message_user(
            request,
            f"Discount duplicated as '{new_discount.name}'. Please review and activate.",
            messages.SUCCESS,
        )


class BulkAssignDiscountForm(forms.Form):
    """Form for bulk assigning discount usages to users."""

    discount = forms.ModelChoiceField(
        queryset=Discount.objects.filter(is_active=True),
        help_text="Select the discount to assign",
    )
    usages_per_user = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        help_text="How many usages to give each user",
    )
    target_role = forms.ChoiceField(
        choices=[
            ("", "All Roles"),
            ("homeowner", "Homeowner"),
            ("handyman", "Handyman"),
        ],
        required=False,
        help_text="Filter by user role",
    )
    registered_after = forms.DateField(
        required=False, help_text="Users registered on or after this date (YYYY-MM-DD)"
    )
    registered_before = forms.DateField(
        required=False, help_text="Users registered on or before this date (YYYY-MM-DD)"
    )


@admin.register(UserDiscountUsage)
class UserDiscountUsageAdmin(ModelAdmin):
    """Admin for viewing discount usages."""

    list_display = [
        "user",
        "discount",
        "job",
        "usage_number",
        "used_at",
    ]

    list_filter = [
        "discount__target_role",
        "used_at",
        "discount",
    ]

    search_fields = [
        "user__email",
        "user__phone_number",
        "discount__code",
        "discount__name",
    ]

    readonly_fields = ["user", "discount", "job", "used_at", "usage_number"]
    ordering = ["-used_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
