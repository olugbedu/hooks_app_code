from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class CustomUserManager(BaseUserManager):
    """Manager for custom user model with email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a user with an email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Plan(models.Model):
    """Model representing a subscription plan."""
    stripe_price_id = models.CharField(max_length=255, null=True)
    name = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    price_per_hook = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    hook_limit = models.IntegerField(default=0)

class StripeCustomer(models.Model):
    """Model representing a Stripe customer."""
    user = models.ForeignKey('User', on_delete=models.CASCADE, null=True)
    stripe_customer_id = models.CharField(max_length=255)

class Subscription(models.Model):
    """Model representing a subscription linked to a plan and customer."""
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=255, null=True)
    customer = models.ForeignKey(StripeCustomer, on_delete=models.CASCADE, null=True)
    hooks = models.IntegerField(default=0)
    merge_credits = models.IntegerField(blank=True, null=True)
    current_period_end = models.IntegerField(default=0)

class User(AbstractUser):
    """Custom user model extending Django's AbstractUser."""
    email = models.EmailField(unique=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        """Override save method to set username as email."""
        self.username = self.email
        super().save(*args, **kwargs)

    def can_generate_video(self):
        """Check if the user can generate a video based on subscription hooks."""
        return self.subscription.hooks >= 1
