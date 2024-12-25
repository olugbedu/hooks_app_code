from django.urls import path
from . import views  # Import views from the current package

app_name = 'account'  # Set the application namespace

# Define URL patterns for the account app
urlpatterns = [
    path("", views.home, name="home"),  # Home page
    path("stage/", views.stage, name="stage"),  # Stage page
    path("login/", views.login_view, name="login"),  # Login page
    path("logout/", views.logout_user, name="logout"),  # Logout page
    path("register/", views.register, name="register"),  # Registration page
    path("subscription/", views.subscription, name="subscription"),  # Subscription page
    path("verify/<str:token>", views.verify, name="verify"),  # Email verification
    path("subscribe/<str:price_id>", views.subscribe, name="subscribe"),  # Subscribe to a plan
    path("stripe-webhook", views.stripe_webhook, name="stripe_webhook"),  # Stripe webhook endpoint
    path("manage-subscription", views.manage_subscription, name="manage_subscription"),  # Manage subscription
    path("billing-portal", views.billing_portal, name="billing_portal"),  # Billing portal
    path("add-credits/<str:kind>", views.add_credits, name="add_credits"),  # Add credits
    path("add-credits-success", views.add_credits_success, name="add_credits_success"),  # Add credits success page
    path("add-credits-cancel", views.add_credits_cancel, name="add_credits_cancel"),  # Add credits cancel page
    path("upgrade-subscription/<str:price_id>", views.upgrade_subscription, name="upgrade_subscription"),  # Upgrade subscription
    path("downgrade-subscription", views.downgrade_subscription, name="downgrade_subscription"),  # Downgrade subscription
    path("cancel-subscription", views.cancel_subscription, name="cancel_subscription"),  # Cancel subscription
    path("terms-and-conditions", views.terms_and_conditions, name="terms_and_conditions"),  # Terms and conditions
    path("privacy-policy", views.privacy_policy, name="privacy_policy"),  # Privacy policy
    path("refund-policy", views.refund_policy, name="refund_policy"),  # Refund policy
    path("affiliate-program", views.affiliate_program, name="affiliate_program"),  # Affiliate program
]
