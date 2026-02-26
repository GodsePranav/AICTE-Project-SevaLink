from django.db import models
from django.conf import settings

class ServiceJob(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('On the Way', 'On the Way'),
        ('Arrived', 'Arrived'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    CATEGORY_CHOICES = (
        ('Plumbing', 'Plumbing'),
        ('Electrical', 'Electrical'),
        ('Cleaning', 'Cleaning'),
        ('HVAC', 'HVAC'),
        ('Carpentry', 'Carpentry'),
        ('Mechanic', 'Mechanic'),
        ('Housekeeping', 'Housekeeping'),
        ('Guard', 'Guard / Security'),
        ('Packing', 'Packing / Moving'),
        ('AC Repair', 'AC Repair'),
        ('Painting', 'Painting'),
        ('Other', 'Other'),
    )

    provider = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='jobs_provided', on_delete=models.CASCADE)
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='jobs_assigned', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    description = models.TextField()
    address = models.CharField(max_length=500, blank=True, default='', help_text="Human-readable address")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()
    scheduled_time = models.DateTimeField(null=True, blank=True, help_text="When the job should be done (null = ASAP)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # Rating field
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    review = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.status}"

class ServiceRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('assigned', 'Assigned'),
    )
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_service_requests', on_delete=models.CASCADE)
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_service_requests', on_delete=models.CASCADE)
    job = models.ForeignKey('ServiceJob', related_name='service_requests', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Request from {self.provider.username} to {self.worker.username} ({self.status})"

class JobApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    job = models.ForeignKey(ServiceJob, related_name='applications', on_delete=models.CASCADE)
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='job_applications', on_delete=models.CASCADE)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Application from {self.worker.username} for {self.job.title} ({self.status})"


class JobTracking(models.Model):
    job = models.OneToOneField(ServiceJob, on_delete=models.CASCADE, related_name='tracking')
    current_lat = models.FloatField(null=True, blank=True)
    current_lon = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    eta_minutes = models.IntegerField(null=True, blank=True)
    delay_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Tracking for Job #{self.job.id}"
