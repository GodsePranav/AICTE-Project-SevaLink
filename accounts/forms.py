from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    # Only 4 essential fields as requested: Full Name, Email, Password (handled by UserCreationForm natively), User Type
    full_name = forms.CharField(label='Full Name as per Aadhaar', max_length=255, required=True)
    email = forms.EmailField(label='Professional Email', max_length=254, required=True)
    phone_number = forms.CharField(
        label='Phone Number (10 digits)',
        required=True,
        widget=forms.TextInput(attrs={
            'pattern': r'\d{10}',
            'maxlength': '10',
            'minlength': '10',
            'title': 'Must be exactly 10 digits',
        })
    )
    aadhaar_number = forms.CharField(
        label='Aadhaar Number (12 digits)',
        required=True,
        widget=forms.TextInput(attrs={
            'pattern': r'\d{12}',
            'maxlength': '12',
            'minlength': '12',
            'title': 'Must be exactly 12 digits',
        })
    )
    username = forms.CharField(
        label='Unique Username', 
        max_length=150, 
        required=True,
        help_text='Letters, numbers, and @/./+/-/_ only.',
        widget=forms.TextInput(attrs={'class': 'w-full'})
    )
    
    ROLE_UI_CHOICES = (
        ('Worker', 'I want to work / provide a service'),
        ('Job Provider', 'I want to hire / find a service'),
    )
    role = forms.ChoiceField(
        choices=ROLE_UI_CHOICES, 
        required=True, 
        label="User Type",
        widget=forms.RadioSelect(attrs={'class': 'peer hidden'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'full_name', 'phone_number', 'aadhaar_number', 'role')

    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        if not email.lower().endswith('@gmail.com'):
            raise forms.ValidationError("You must register using a @gmail.com email address.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email')

        # Split full name into first and last name for Django's native User model if needed
        name_parts = self.cleaned_data.get('full_name').split(' ', 1)
        user.first_name = name_parts[0]
        if len(name_parts) > 1:
            user.last_name = name_parts[1]

        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                role=self.cleaned_data.get('role'),
                full_name=self.cleaned_data.get('full_name'),
                phone_number=self.cleaned_data.get('phone_number'),
                aadhaar_number=self.cleaned_data.get('aadhaar_number')
            )
        return user

class UserEditForm(forms.ModelForm):
    username = forms.CharField(
        label='Username', 
        max_length=150, 
        required=True,
        help_text='Unique username for your profile.'
    )
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(max_length=254, required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        if not email.lower().endswith('@gmail.com'):
            raise forms.ValidationError("You must use a @gmail.com email address.")
        
        # Check uniqueness, ignoring the current user
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken. Please choose another one.")
        return username

class ProfileEditForm(forms.ModelForm):
    is_available = forms.BooleanField(
        label='Work Availability Status',
        required=False,
        help_text="Toggle: 'Available Now' vs 'Busy'"
    )
    
    class Meta:
        model = Profile
        fields = (
            'profile_picture',
            'full_name',
            'phone_number',
            'aadhaar_number',
            'primary_category',
            'job_title',
            'service_skills',
            'years_experience',
            'is_available',
            'live_location'
        )
        labels = {
            'full_name': 'Full Name (Must match Aadhaar)',
            'phone_number': 'Phone Number (For OTP Verification)',
            'aadhaar_number': '12-Digit Aadhaar Number',
            'primary_category': 'Work Category',
            'job_title': 'Job Title / Specific Trade',
            'service_skills': 'Service Skills',
            'years_experience': 'Years of Experience',
            'is_available': 'Work Availability Status',
            'live_location': 'Service Area / Live Location',
        }
        widgets = {
            'service_skills': forms.Textarea(attrs={'rows': 3}),
            'live_location': forms.Textarea(attrs={'rows': 2, 'placeholder': '{"lat": 0.0, "lon": 0.0} (or empty)'}),
            'aadhaar_number': forms.TextInput(attrs={
                'pattern': r'\d{12}',
                'maxlength': '12',
                'minlength': '12',
                'title': 'Must be exactly 12 digits',
            }),
            'phone_number': forms.TextInput(attrs={
                'pattern': r'\d{10}',
                'maxlength': '10',
                'minlength': '10',
                'title': 'Must be exactly 10 digits',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and getattr(self.instance, 'is_verified', False):
            self.fields['aadhaar_number'].disabled = True
            self.fields['full_name'].disabled = True

    def clean_live_location(self):
        data = self.cleaned_data.get('live_location')
        if not data:
            return None
        if isinstance(data, str):
            import json
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Please provide valid JSON")
        return data

    def save(self, commit=True):
        profile = super().save(commit=False)
        if profile.live_location and isinstance(profile.live_location, dict):
            profile.latitude = profile.live_location.get('lat')
            profile.longitude = profile.live_location.get('lon')
        if commit:
            profile.save()
        return profile
