"""
cart/forms.py — Address form with proper validation.
"""
from django import forms
from .models import Address


class AddressForm(forms.ModelForm):
    class Meta:
        model  = Address
        fields = ['full_name', 'phone', 'house_no', 'street', 'city', 'state', 'pincode', 'is_default']
        widgets = {
            'full_name':  forms.TextInput(attrs={'placeholder': 'Full name of recipient'}),
            'phone':      forms.TextInput(attrs={'placeholder': '+919876543210'}),
            'house_no':   forms.TextInput(attrs={'placeholder': 'House / Flat No.'}),
            'street':     forms.TextInput(attrs={'placeholder': 'Street / Area / Landmark'}),
            'city':       forms.TextInput(attrs={'placeholder': 'City'}),
            'state':      forms.TextInput(attrs={'placeholder': 'State'}),
            'pincode':    forms.TextInput(attrs={'placeholder': '6-digit PIN code', 'maxlength': '6'}),
        }

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode', '')
        if not pincode.isdigit() or len(pincode) != 6:
            raise forms.ValidationError('PIN code must be exactly 6 digits.')
        return pincode
