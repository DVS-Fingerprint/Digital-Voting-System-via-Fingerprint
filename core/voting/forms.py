from django import forms
from .models import Voter, FingerprintTemplate

class VoterRegistrationForm(forms.ModelForm):
    template_hex = forms.ModelChoiceField(
        queryset=FingerprintTemplate.objects.order_by('-created_at')[:20],
        required=True,
        label='Fingerprint Template',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Select a fingerprint template',
        to_field_name='template_hex',
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
