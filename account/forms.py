from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.conf import settings

# Custom login form inheriting from Django's AuthenticationForm
class CustomLoginForm(AuthenticationForm):
    # Username field with email input type
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'id': 'email',  # HTML id attribute
            'type': 'email',  # Input type as email
            'placeholder': 'Email'  # Placeholder text
        })
    )
    # Password field with password input type
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'id': 'password',  # HTML id attribute
            'type': 'password',  # Input type as password
            'placeholder': 'Password'  # Placeholder text
        })
    )

# Contact us form for user inquiries
class ContactUsForm(forms.Form):
    # Full name field with a maximum length of 100 characters
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "id": "full_name",  # HTML id attribute
            "placeholder": "Enter Your Full Name",  # Placeholder text
            "type": "text"  # Input type as text
        })
    )
    # Email field with email input type
    email = forms.EmailField(
        widget=forms.TextInput(attrs={
            "id": "email",  # HTML id attribute
            "placeholder": "Enter your Email address",  # Placeholder text
            "type": "email"  # Input type as email
        })
    )
    # Message field with a textarea input
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            "id": "message",  # HTML id attribute
            'placeholder': "Write Us Your Question Here..."  # Placeholder text
        })
    )

    # Method to send the contact form data via email
    def send(self):
        # Construct the message from form data
        message = (
            f"Full Name: {self.cleaned_data['full_name']}\n"
            f"Email: {self.cleaned_data['email']}\n"
            f"Message: {self.cleaned_data['message']}\n"
        )
        # Send the email using Django's send_mail function
        send_mail(
            "Contact Us Form Submission",  # Subject
            message,  # Message body
            from_email=settings.EMAIL_HOST_USER,  # From email
            recipient_list=[settings.EMAIL_HOST_USER],  # Recipient list
            fail_silently=False,  # Raise an error if sending fails
        )
