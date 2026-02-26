from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Profile
from datetime import date, timedelta
import re

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    # Only 4 essential fields as requested: Full Name, Email, Password (handled by UserCreationForm natively), User Type
    full_name = forms.CharField(label='Full Name (As per Aadhaar)', max_length=255, required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Pranav Godse', 'autocomplete': 'name'}))
    email = forms.EmailField(label='Email Address', max_length=254, required=True,
        widget=forms.TextInput(attrs={'placeholder': 'you@example.com', 'autocomplete': 'email'}))
    phone_number = forms.CharField(
        label='Phone Number',
        required=True,
        widget=forms.TextInput(attrs={
            'type': 'tel',
            'pattern': r'\d{10}',
            'maxlength': '10',
            'minlength': '10',
            'inputmode': 'numeric',
            'placeholder': '9876543210',
            'title': 'Must be exactly 10 digits',
            'autocomplete': 'tel',
        })
    )
    aadhaar_number = forms.CharField(
        label='Aadhaar Number',
        required=True,
        widget=forms.TextInput(attrs={
            'pattern': r'\d{12}',
            'maxlength': '12',
            'minlength': '12',
            'inputmode': 'numeric',
            'placeholder': '123456789012',
            'title': 'Must be exactly 12 digits',
        })
    )
    username = forms.CharField(
        label='Username',
        max_length=30,
        min_length=3,
        required=True,
        help_text='3-30 characters. Letters, numbers, and @/./+/-/_ only.',
        widget=forms.TextInput(attrs={'placeholder': 'Choose a username', 'autocomplete': 'username'})
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
    gender = forms.ChoiceField(
        choices=[('', '-- Select Gender --'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        required=False,
        label='Gender'
    )
    date_of_birth = forms.DateField(
        required=False,
        label='Date of Birth',
        widget=forms.DateInput(attrs={'type': 'date', 'max': str(date.today())})
    )
    profile_picture = forms.ImageField(
        required=False,
        label='Profile Picture',
        widget=forms.ClearableFileInput(attrs={'accept': 'image/*'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'full_name', 'phone_number', 'aadhaar_number', 'role')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise forms.ValidationError("Please enter a valid email address.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if not re.match(r'^[a-zA-Z\s]+$', name):
            raise forms.ValidationError("Full name must contain only letters and spaces.")
        parts = name.split()
        if len(parts) < 2:
            raise forms.ValidationError("Please enter your first and last name (at least 2 words).")
        return name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if not re.match(r'^\d{10}$', phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean_aadhaar_number(self):
        aadhaar = self.cleaned_data.get('aadhaar_number', '').strip()
        if not re.match(r'^\d{12}$', aadhaar):
            raise forms.ValidationError("Aadhaar number must be exactly 12 digits.")
        return aadhaar

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3:
            raise forms.ValidationError("Username must be at least 3 characters.")
        if len(username) > 30:
            raise forms.ValidationError("Username must be 30 characters or fewer.")
        if not re.match(r'^[\w.@+-]+$', username):
            raise forms.ValidationError("Username can only contain letters, numbers, and @/./+/-/_ characters.")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        role = self.cleaned_data.get('role', 'Job Provider')
        if dob:
            today = date.today()
            if dob >= today:
                raise forms.ValidationError("Date of birth must be in the past.")
            age = (today - dob).days // 365
            if role == 'Worker' and age < 18:
                raise forms.ValidationError("Workers must be at least 18 years old to register.")
            elif role == 'Job Provider' and age < 12:
                raise forms.ValidationError("You must be at least 12 years old to register.")
            if age > 120:
                raise forms.ValidationError("Please enter a valid date of birth.")
        return dob

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
            profile = Profile.objects.create(
                user=user,
                role=self.cleaned_data.get('role'),
                full_name=self.cleaned_data.get('full_name'),
                phone_number=self.cleaned_data.get('phone_number'),
                aadhaar_number=self.cleaned_data.get('aadhaar_number'),
                gender=self.cleaned_data.get('gender') or '',
                date_of_birth=self.cleaned_data.get('date_of_birth')
            )
            # Save optional profile picture
            pic = self.cleaned_data.get('profile_picture')
            if pic:
                profile.profile_picture = pic
                profile.save()
        return user

class UserEditForm(forms.ModelForm):
    username = forms.CharField(
        label='Username', 
        max_length=150, 
        required=True,
        help_text='Unique username for your profile.'
    )
    email = forms.EmailField(label='Email Address', max_length=254, required=True)

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise forms.ValidationError("Please enter a valid email address.")
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
            'gender',
            'date_of_birth',
            'primary_category',
            'job_title',
            'service_skills',
            'years_experience',
            'is_available',
            'live_location'
        )
        labels = {
            'full_name': 'Full Name (As per Aadhaar)',
            'phone_number': 'Phone Number',
            'aadhaar_number': 'Aadhaar Number',
            'gender': 'Gender',
            'date_of_birth': 'Date of Birth',
            'primary_category': 'Service Category',
            'job_title': 'Job Title',
            'service_skills': 'Skills',
            'years_experience': 'Experience (Years)',
            'is_available': 'Availability',
            'live_location': 'Location',
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
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Full name is always locked (set during signup from Aadhaar)
        self.fields['full_name'].disabled = True
        if self.instance and getattr(self.instance, 'is_verified', False):
            self.fields['aadhaar_number'].disabled = True

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if name:
            if not re.match(r'^[a-zA-Z\s]+$', name):
                raise forms.ValidationError("Full name must contain only letters and spaces.")
            if len(name.split()) < 2:
                raise forms.ValidationError("Please enter first and last name (at least 2 words).")
        return name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if phone and not re.match(r'^\d{10}$', phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

    def clean_aadhaar_number(self):
        aadhaar = self.cleaned_data.get('aadhaar_number', '').strip()
        if aadhaar and not re.match(r'^\d{12}$', aadhaar):
            raise forms.ValidationError("Aadhaar number must be exactly 12 digits.")
        return aadhaar

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        role = self.instance.role if self.instance else 'Job Provider'
        if dob:
            today = date.today()
            if dob >= today:
                raise forms.ValidationError("Date of birth must be in the past.")
            age = (today - dob).days // 365
            if role == 'Worker' and age < 18:
                raise forms.ValidationError("Workers must be at least 18 years old.")
            elif role == 'Job Provider' and age < 12:
                raise forms.ValidationError("You must be at least 12 years old.")
            if age > 120:
                raise forms.ValidationError("Please enter a valid date of birth.")
        return dob

    def clean_years_experience(self):
        exp = self.cleaned_data.get('years_experience')
        if exp is not None:
            if exp < 0 or exp > 60:
                raise forms.ValidationError("Experience must be between 0 and 60 years.")
        return exp

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
