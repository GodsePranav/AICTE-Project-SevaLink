from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )
    list_display = ('username', 'email', 'get_role', 'get_is_verified', 'is_staff')
    list_select_related = ('profile', )
    
    def get_role(self, instance):
        return instance.profile.role
    get_role.short_description = 'Role'
    
    def get_is_verified(self, instance):
        return instance.profile.is_verified
    get_is_verified.short_description = 'Verified'
    get_is_verified.boolean = True

admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_verified', 'latitude', 'longitude')
    list_filter = ('role', 'is_verified')
    search_fields = ('user__username', 'user__email')
    filter_horizontal = ('connections',)
