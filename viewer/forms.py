from django import forms
from django.core.exceptions import ValidationError
from .models import Facility
import re


class FacilityForm(forms.ModelForm):
    """Custom form for Facility with AE Title validation"""
    
    class Meta:
        model = Facility
        fields = ['name', 'address', 'phone', 'email', 'letterhead_logo', 'ae_title']
        widgets = {
            'ae_title': forms.TextInput(attrs={
                'maxlength': 16,
                'pattern': '[A-Z0-9]*',
                'title': 'Only uppercase letters and numbers allowed'
            })
        }
    
    def clean_ae_title(self):
        """Validate AE Title field"""
        ae_title = self.cleaned_data.get('ae_title')
        
        if ae_title:
            # Check if it contains only alphanumeric characters
            if not re.match(r'^[A-Z0-9]+$', ae_title):
                raise ValidationError(
                    'AE Title must contain only uppercase letters and numbers.'
                )
            
            # Check length
            if len(ae_title) > 16:
                raise ValidationError(
                    'AE Title must be 16 characters or less.'
                )
            
            # Check uniqueness (exclude current instance in case of update)
            qs = Facility.objects.filter(ae_title=ae_title)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise ValidationError(
                    'This AE Title is already in use by another facility.'
                )
        
        return ae_title