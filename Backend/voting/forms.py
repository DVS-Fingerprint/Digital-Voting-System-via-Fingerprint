from django import forms
from .models import Voter

class VoterRegistrationForm(forms.ModelForm):
    class Meta:
        model = Voter
        fields = ['full_name', 'voter_id', 'fingerprint_id']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'voter_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Voter ID'}),
            'fingerprint_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Fingerprint ID'}),
        }
