from django import forms
from django.forms import formset_factory

class VideoUploadForm(forms.Form):
    video = forms.FileField()
    

# VideoUploadFormSet = formset_factory(VideoUploadForm, extra=5)  # Adjust 'extra' as needed
