import csv

from django.contrib import admin
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html

from .models import Application, ApplicationPhoto
from .sharing import application_share_token


class ApplicationPhotoInline(admin.TabularInline):
    model = ApplicationPhoto
    extra = 0
    readonly_fields = ["photo_type", "photo_preview", "original_name", "uploaded_at"]
    fields = ["photo_type", "photo_preview", "original_name", "uploaded_at"]

    @admin.display(description="Photo")
    def photo_preview(self, obj):
        if obj is None or not obj.pk:
            return "Save the photo to preview it."
        token = application_share_token(obj.application)
        url = reverse(
            "camp:shared_photo", args=[token, obj.pk]
        )
        return format_html(
            '<a href="{0}" target="_blank" rel="noopener">'
            '<img src="{0}" alt="{1}" width="90" height="90" '
            'style="object-fit:cover"></a>',
            url,
            obj.original_name,
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("application")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "application_number",
        "kind",
        "full_name",
        "email",
        "phone",
        "submitted_at",
        "status",
    ]
    list_filter = ["kind", "status", "submitted_at"]
    search_fields = [
        "application_number",
        "kind",
        "full_name",
        "email",
        "phone",
        "city",
        "town",
        "whatsapp_number",
        "social_handle",
        "tiktok_handle",
    ]
    readonly_fields = [
        "application_number",
        "share_token",
        "submitted_at",
        "updated_at",
        "secure_application_link",
        "secure_photos_link",
    ]
    fieldsets = [
        (
            "Applicant",
            {
                "fields": (
                    "application_number",
                    "full_name",
                    "email",
                    "phone",
                    "whatsapp_number",
                    "age",
                    "age_category",
                    "gender",
                    "shoe_size",
                    "pants_size",
                    "dress_size",
                    "skirt_size",
                    "top_size",
                    "city",
                    "town",
                    "current_occupation",
                    "preferred_days",
                    "available_full_five_weeks",
                    "has_modelling_experience",
                    "previous_experience",
                    "social_handle",
                    "tiktok_handle",
                    "about",
                    "guardian_name",
                    "guardian_phone",
                    "secure_application_link",
                    "secure_photos_link",
                )
            },
        ),
        ("Review", {"fields": ("status", "submitted_at", "updated_at")}),
        ("Private link token", {"fields": ("share_token",)}),
        (
            "Consent",
            {
                "fields": (
                    "privacy_consent",
                    "photo_consent",
                    "guardian_consent",
                )
            },
        ),
    ]
    inlines = [ApplicationPhotoInline]
    actions = ["export_csv"]

    @admin.action(description="Export selected applications to CSV")
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="applications.csv"'
        response["Cache-Control"] = "private, no-store"
        writer = csv.writer(response)
        field_names = [f.name for f in Application._meta.concrete_fields]
        writer.writerow(field_names)
        for application in queryset:
            writer.writerow(
                [
                    "'" + str(value)
                    if isinstance(value, str) and value[:1] in "=+-@"
                    else value
                    for value in (getattr(application, name) for name in field_names)
                ]
            )
        return response

    @admin.display(description="Secure full application")
    def secure_application_link(self, obj):
        if not obj or not obj.pk:
            return "Available after the application is saved."
        url = reverse(
            "camp:shared_application",
            args=[application_share_token(obj)],
        )
        return format_html('<a href="{0}" target="_blank">{0}</a>', url)

    @admin.display(description="Secure photographs")
    def secure_photos_link(self, obj):
        if not obj or not obj.pk:
            return "Available after the application is saved."
        url = reverse(
            "camp:shared_photos",
            args=[application_share_token(obj)],
        )
        return format_html('<a href="{0}" target="_blank">{0}</a>', url)
