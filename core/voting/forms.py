from django import forms
from .models import Voter

class VoterRegistrationForm(forms.ModelForm):
    template_hex = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Paste fingerprint template hex here'}),
        required=True,
        label='Fingerprint Template (Hex)'
    )
    class Meta:
        model = Voter
        fields = ['voter_id', 'name', 'fingerprint_id', 'age', 'gender']
        widgets = {
            'voter_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Voter ID'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'fingerprint_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Fingerprint ID'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age'}),
            'gender': forms.Select(choices=[('','Select'),('Male','Male'),('Female','Female'),('Other','Other')], attrs={'class': 'form-control'}),
        }
