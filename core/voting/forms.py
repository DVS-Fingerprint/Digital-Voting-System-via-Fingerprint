from django import forms
from .models import Voter

class VoterRegistrationForm(forms.ModelForm):
    class Meta:
        model = Voter
        fields = ['name', 'uid']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'uid': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Fingerprint UID'}),
        }
