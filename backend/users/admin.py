from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Subscription


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'telegram_id', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'telegram_id')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Telegram Integration', {'fields': ('telegram_id',)}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Telegram Integration', {'fields': ('telegram_id',)}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author', 'created')
    list_filter = ('created',)
    search_fields = ('user__username', 'author__username')
    ordering = ('-created',)
