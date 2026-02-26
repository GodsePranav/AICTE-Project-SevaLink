from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class CustomUser(AbstractUser):
    pass

class Profile(models.Model):
    ROLE_CHOICES = (
        ('Worker', 'Worker'),
        ('Job Provider', 'Job Provider'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Job Provider')
    
    # Generic fields for all
    CATEGORY_CHOICES = (
        ('Professional', 'Professional'),
        ('Skilled Trade', 'Skilled Trade'),
        ('General Labor', 'General Labor'),
    )
    
    full_name = models.CharField(max_length=255, blank=True, help_text="Must match government ID.")
    aadhaar_number = models.BigIntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(100000000000), MaxValueValidator(999999999999)],
        help_text="12-digit Aadhaar Number"
    )
    primary_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., 'Python Developer', 'House Guard'")
    phone_number = models.BigIntegerField(null=True, blank=True, help_text="Essential for OTP")
    live_location = models.JSONField(null=True, blank=True, help_text="For Map/3D globe pins")
    is_available = models.BooleanField(default=True, help_text="Toggle: 'Available Now' vs 'Busy'")
    is_verified = models.BooleanField(default=False)
    
    # Location for all users (Haversine formula mapping via SQLite)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Professional specifics
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    
    # Profile picture
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    # Trade-Skills specifics
    service_skills = models.TextField(blank=True, help_text="List your specific skills, e.g., Housekeeping, Guard, Mechanic")
    years_experience = models.PositiveIntegerField(null=True, blank=True, help_text="Years of work experience")
    rating = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(5)], help_text="Average rating 0-5")
    
    # Social Connections (Followers/Following)
    connections = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)

    @property
    def service_skills_list(self):
        """Return skills as a list for template iteration."""
        if self.service_skills:
            return [s.strip() for s in self.service_skills.split(',') if s.strip()]
        return []

    def __str__(self):
        return f"{self.user.username}'s Profile"
