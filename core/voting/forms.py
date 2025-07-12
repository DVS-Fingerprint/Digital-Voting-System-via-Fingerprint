from django import forms
from .models import Voter

class VoterRegistrationForm(forms.ModelForm):
    class Meta:
        model = Voter
        fields = ['name', 'email', 'fingerprint_id']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'fingerprint_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Fingerprint ID'}),
        }
