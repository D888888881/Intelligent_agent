from django.contrib import admin

from .models import GeneratedImage, GenerationJob


class GeneratedImageInline(admin.TabularInline):
    model = GeneratedImage
    extra = 0


@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "completed_count", "image_count", "created_at")
    inlines = [GeneratedImageInline]
