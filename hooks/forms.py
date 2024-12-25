from django import forms
from .models import Hook

class HookForm(forms.ModelForm):
    class Meta:
        # Specify the model to use for the form
        model = Hook
        
        # Define the fields to include in the form
        fields = [
            'hooks_content', 'google_sheets_link', 'eleven_labs_api_key', 
            'voice_id', 'box_color', 'font_color'
        ]

        # Define custom widgets for each field
        widgets = {
            'hooks_content': forms.ClearableFileInput(attrs={
                'id': 'hooks',  # HTML id attribute
                'accept': 'video/mp4,video/x-m4v,video/*',  # Accepted file types
            }),
            'google_sheets_link': forms.URLInput(attrs={
                'id': 'google_link',  # HTML id attribute
                'placeholder': 'Paste URL Link',  # Placeholder text
            }),
            'eleven_labs_api_key': forms.TextInput(attrs={
                'id': 'api_key',  # HTML id attribute
                'placeholder': 'Paste API Key',  # Placeholder text
            }),
            'voice_id': forms.TextInput(attrs={
                'id': 'voice_id',  # HTML id attribute
                'placeholder': 'Enter Voice ID',  # Placeholder text
            }),
            'box_color': forms.TextInput(attrs={
                'type': 'color',  # Input type for color selection
                'class': 'color-input',  # CSS class for styling
                'value': '#485AFF',  # Default color value
                'id': 'boxcolor',  # HTML id attribute
                'required': 'required',  # Field is required
            }),
            'font_color': forms.TextInput(attrs={
                'type': 'color',  # Input type for color selection
                'class': 'color-input',  # CSS class for styling
                'value': '#FFFFFF',  # Default color value
                'id': 'fontcolor',  # HTML id attribute
                'required': 'required',  # Field is required
            }),
        }
