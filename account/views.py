# Import necessary modules and functions from Django and other libraries
from account.forms import ContactUsForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth import login, get_user_model, logout, authenticate
from django.contrib import messages
from django.core.mail import EmailMessage, send_mail
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from .models import Subscription, StripeCustomer, Plan
import stripe
import uuid
from datetime import datetime

# Render the stage page
def stage(request):
    # Render the 'stage.html' template
    return render(request, 'stage.html')

# Handle user login
def login_view(request):
    # If the user is already authenticated, redirect to the upload page
    if request.user.is_authenticated:
        return redirect('hooks:upload')

    # If the request method is POST, process the login form
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, username=email, password=password)

        # If the user is authenticated and email is verified, log them in
        if user:
            if not user.verification_token:
                _login(request, user)
                try:
                    return redirect(request.session.get('next'))
                except:
                    return redirect('hooks:upload')
            else:
                messages.error(request, 'Your Email Address Is Not Verified. Please Verify Your Email Before Logging In.')
        else:
            messages.error(request, 'Invalid Username or Password. Please Try Again.')

    # Store the next URL in the session and render the login page
    request.session['next'] = request.GET.get('next', '')
    return render(request, 'registration/login.html')

# Handle user logout
def logout_user(request):
    # If the user is authenticated, log them out
    if request.user.is_authenticated:
        logout(request)
    # Redirect to the home page
    return redirect('account:home')

# Render the home page and handle contact form submission
def home(request):
    # If the user is authenticated, redirect to the upload page
    if request.user.is_authenticated:
        return redirect('hooks:upload')

    # Initialize the contact form
    contact_us_form = ContactUsForm(request.POST or None)

    # If the request method is POST and the form is valid, send the contact message
    if request.method == 'POST' and contact_us_form.is_valid():
        try:
            contact_us_form.send()
            messages.success(request, 'Message Sent Successfully')
        except Exception as e:
            print(f'An error occurred while sending contact us message {e}')
            messages.error(request, 'Failed To Send Message')
        return redirect(reverse('account:home') + '#Contact')

    # Render the home page with the contact form and available plans
    return render(request, 'home.html', {'contact_us_form': contact_us_form, 'plans': Plan.objects.all()})

# Render terms and conditions page
def terms_and_conditions(request):
    # Render the 'terms_and_conditions.html' template
    return render(request, 'terms_and_conditions.html')

# Render privacy policy page
def privacy_policy(request):
    # Render the 'privacy_policy.html' template
    return render(request, 'privacy_policy.html')

# Render refund policy page
def refund_policy(request):
    # Render the 'refund_policy.html' template
    return render(request, 'refund_policy.html')

# Render affiliate program page
def affiliate_program(request):
    # Render the 'affiliate_program.html' template
    return render(request, 'affiliate_program.html')

# Handle user registration
def register(request):
    # If the request method is POST, process the registration form
    if request.method == 'POST':
        stripe.api_key = settings.STRIPE_SEC_KEY
        checkout_session_id = request.POST.get('session_id')
        name, email, password1, password2 = request.POST.get('name'), request.POST.get('email'), request.POST.get('password1'), request.POST.get('password2')

        # Validate the passwords and check if the email is already registered
        if len(password1) < 6:
            messages.error(request, 'At Least 6 Characters Are Required')
        elif password1 != password2:
            messages.error(request, 'Passwords Do Not Match.')
        elif get_user_model().objects.filter(email=email).exists():
            messages.error(request, 'This Email Is Already Registered.')
        else:
            # Create a new user and handle the subscription
            user = get_user_model().objects.create_user(email=email, password=password1, first_name=name)
            user.save()
            handle_subscription(user, checkout_session_id)
            return render(request, 'registration/register.html', context={'price_id': 'free', 'success': True})

        # Render the registration page with the session ID
        return render(request, 'registration/register.html', context={'session_id': checkout_session_id})

    # Render the registration page with the session ID from the GET request
    return render(request, 'registration/register.html', context={'session_id': request.GET.get('session_id')})

# Handle subscription logic during registration
def handle_subscription(user, checkout_session_id):
    # If no checkout session ID is provided, assign a free plan to the user
    if checkout_session_id is None:
        free_plan = Plan.objects.get(id=3)
        customer = stripe.Customer.create(email=user.email, name=user.first_name)
        stripe_customer = StripeCustomer(user=user, stripe_customer_id=customer.id)
        stripe_customer.save()
        subscription = Subscription(plan=free_plan, hooks=free_plan.hook_limit, merge_credits=free_plan.hook_limit * 5, customer=stripe_customer)
        subscription.save()
        user.subscription = subscription
        user.verification_token = str(uuid.uuid4())
        user.save()
        send_html_email2('Welcome to HooksMaster.io – Verify Your Email To Continue', None, settings.EMAIL_HOST_USER, user.email, 'verification.html', {'first_name': user.first_name, 'verification_url': settings.DOMAIN + reverse('account:verify', kwargs={'token': user.verification_token})})
    else:
        # Retrieve the checkout session and assign the subscription to the user
        checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)
        stripe_customer_id = checkout_session.customer
        customer = StripeCustomer.objects.get_or_create(stripe_customer_id=stripe_customer_id, defaults={'user': user})[0]
        customer.user = user
        customer.save()
        subscription = Subscription.objects.get(customer_id=customer.id)
        user.subscription = subscription
        user.save()
        send_confirmation_email(user.email, user.first_name)
        _login(request, user)
        return redirect("hooks:upload")

# Handle Stripe webhook events
@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SEC_KEY
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']

    # Verify the Stripe webhook signature
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    # Handle different types of Stripe events
    event_type = event['type']
    event_object = event['data']['object']

    if event_type == 'invoice.payment_succeeded':
        handle_payment_succeeded(event_object)
    elif event_type == 'invoice.payment_failed':
        handle_payment_failed(event_object)
    elif event_type == 'customer.subscription.deleted' and event_object.cancel_at_period_end:
        handle_subscription_deleted(event_object)

    return HttpResponse(status=200)

# Handle payment succeeded event
def handle_payment_succeeded(event_object):
    # Handle subscription creation or cycle based on the billing reason
    if event_object.billing_reason == 'subscription_create':
        handle_subscription_create(event_object)
    elif event_object.billing_reason == 'subscription_cycle':
        handle_subscription_cycle(event_object)

# Handle subscription creation
def handle_subscription_create(event_object):
    try:
        customer_id = event_object.customer
        customer = StripeCustomer.objects.get_or_create(stripe_customer_id=customer_id, defaults={'user': None})[0]
        prev_sub = Subscription.objects.filter(customer_id=customer.id).first()
        prev_sub_hooks, prev_sub_merges = (prev_sub.hooks, prev_sub.merge_credits) if prev_sub else (0, 0)
        if prev_sub and prev_sub.stripe_subscription_id:
            stripe.Subscription.delete(prev_sub.stripe_subscription_id)
        plan = Plan.objects.get(stripe_price_id=event_object.lines.data[0].price.id)
        subscription = Subscription(plan=plan, stripe_subscription_id=event_object.subscription, customer=customer, hooks=plan.hook_limit + prev_sub_hooks, merge_credits=(plan.hook_limit * 5) + prev_sub_merges)
        subscription.save()
        if customer.user:
            customer.user.subscription = subscription
            customer.user.save()
            if prev_sub:
                prev_sub.delete()
    except Exception as e:
        print(f'{datetime.now().strftime("%H:%M:%S")}: Error in stripe webhook: {e}')

# Handle subscription cycle event
def handle_subscription_cycle(event_object):
    try:
        plan = Plan.objects.get(stripe_price_id=event_object.lines.data[0].price.id)
        subscription = Subscription.objects.get(stripe_subscription_id=event_object.subscription)
        subscription.hooks += plan.hook_limit
        subscription.merge_credits += plan.hook_limit * 5
        subscription.save()
    except Exception as e:
        print(f'{datetime.now().strftime("%H:%M:%S")}: Error in stripe webhook: {e}')

# Handle payment failed event
def handle_payment_failed(event_object):
    # Log the payment failure based on the billing reason
    if event_object.billing_reason == 'subscription_create':
        print(f'{datetime.now().strftime("%H:%M:%S")}: Payment Failed. Couldn\'t Complete Subscription Successfully. Please try again later.')
    elif event_object.billing_reason == 'subscription_cycle':
        print(f'{datetime.now().strftime("%H:%M:%S")}: Payment Failed. Couldn\'t Renew Subscription Successfully. Please try again later.')

# Handle subscription deletion event
def handle_subscription_deleted(event_object):
    try:
        customer = StripeCustomer.objects.get(stripe_customer_id=event_object.customer)
        sub = Subscription.objects.get(customer_id=customer.id)
        sub.hooks = 0
        sub.merge_credits = 0
        sub.save()
    except StripeCustomer.DoesNotExist:
        return HttpResponse(status=404)

# Manage user subscription
@login_required
def manage_subscription(request):
    # Calculate the remaining credits and days left in the subscription period
    credits_left = request.user.subscription.hooks
    total_credits = max(request.user.subscription.plan.hook_limit, credits_left)
    current_period_end = get_current_period_end(request.user.subscription)
    days_left = max(-1, int((current_period_end - int(datetime.now().timestamp())) / 86400)) + 1

    # Render the subscription management page with the calculated values
    return render(request, 'subscription.html', {
        'total_credits': total_credits,
        'credits_left': credits_left,
        'cur_plan': request.user.subscription.plan,
        'price_per_merge': f"{(request.user.subscription.plan.price_per_hook / 5):.2f}",
        'plans': Plan.objects.all(),
        'days_left': days_left,
    })

# Get current period end for subscription
def get_current_period_end(subscription):
    # Retrieve the current period end from Stripe if the subscription ID is available
    if subscription.stripe_subscription_id:
        stripe.api_key = settings.STRIPE_SEC_KEY
        return int(stripe.Subscription.retrieve(subscription.stripe_subscription_id)['current_period_end'])
    return subscription.current_period_end

# Redirect to Stripe billing portal
@login_required
def billing_portal(request):
    stripe.api_key = settings.STRIPE_SEC_KEY
    try:
        customer = StripeCustomer.objects.get(user_id=request.user.id)
        session = stripe.billing_portal.Session.create(customer=customer.stripe_customer_id, return_url=settings.DOMAIN + reverse('account:home'))
        return redirect(session.url)
    except Exception:
        return redirect(reverse('account:home'))

# Verify user email
def verify(request, token):
    try:
        user = get_user_model().objects.get(verification_token=token)
        if user:
            user.verification_token = None
            user.save()
            _login(request, user)
            return redirect('hooks:upload')
    except:
        return redirect(reverse('account:home'))

# Subscribe to a plan
def subscribe(request, price_id):
    if request.method == 'GET':
        try:
            stripe.api_key = settings.STRIPE_SEC_KEY
            success_path = request.GET.get('success_path')
            cancel_path = request.GET.get('cancel_path')
            customer = request.user.subscription.customer.stripe_customer_id if request.user.is_authenticated else None
            checkout_session = stripe.checkout.Session.create(
                customer=customer,
                success_url=f"{settings.DOMAIN}{success_path}{'&' if '?' in success_path else '?'}session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.DOMAIN}{cancel_path}",
                payment_method_types=['card'],
                mode='subscription',
                line_items=[{'price': price_id, 'quantity': 1}]
            )
            return redirect(checkout_session.url)
        except Exception:
            return redirect(reverse('account:home'))

# Add credits to user account
@login_required
def add_credits(request, kind):
    if request.method == 'POST' and int(request.POST.get('credits_number')) >= 1 and request.user.subscription.plan.name.lower() != 'free':
        try:
            stripe.api_key = settings.STRIPE_SEC_KEY
            unit_amount = float(request.user.subscription.plan.price_per_hook) if kind == 'hook' else float(request.user.subscription.plan.price_per_hook / 5)
            checkout_session = stripe.checkout.Session.create(
                customer=request.user.subscription.customer.stripe_customer_id,
                success_url=f"{settings.DOMAIN}{reverse('account:add_credits_success')}?amount={request.POST.get('credits_number')}&kind={kind}",
                cancel_url=settings.DOMAIN + reverse('account:add_credits_cancel'),
                payment_method_types=['card'],
                line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': f'{request.POST.get("credits_number")} {kind.title()} Credits'}, 'unit_amount': int(round(unit_amount * 100))}, 'quantity': int(request.POST.get('credits_number'))}],
                mode='payment',
            )
            return redirect(checkout_session.url)
        except Exception:
            return redirect(reverse('account:home'))

# Handle successful addition of credits
@login_required
def add_credits_success(request):
    if request.method == 'GET':
        new_credits = int(request.GET.get('amount'))
        kind = request.GET.get('kind')
        if kind == 'hook':
            request.user.subscription.hooks += new_credits
        elif kind == 'merge':
            request.user.subscription.merge_credits += new_credits
        request.user.subscription.save()
        return redirect(reverse('account:manage_subscription') + '?recheck=true')

# Handle cancellation of adding credits
def add_credits_cancel(request):
    return redirect(reverse('account:manage_subscription'))

# Upgrade user subscription
@login_required
def upgrade_subscription(request, price_id):
    return subscribe(request, price_id)

# Downgrade user subscription
@login_required
def downgrade_subscription(request):
    try:
        if request.user.subscription.plan.id == 2:
            subscription = stripe.Subscription.retrieve(request.user.subscription.stripe_subscription_id)
            stripe.Subscription.modify(subscription.id, items=[{'id': subscription['items']['data'][0].id, 'price': settings.STRIPE_PRICE_ID_PRO}], proration_behavior='none')
            pro_plan = Plan.objects.get(id=1)
            request.user.subscription.plan = pro_plan
            request.user.subscription.save()
            return redirect(reverse('account:manage_subscription') + '?recheck=true')
    except Exception:
        return redirect(reverse('account:manage_subscription'))

# Cancel user subscription
@login_required
def cancel_subscription(request):
    stripe.api_key = settings.STRIPE_SEC_KEY
    try:
        subscription = stripe.Subscription.retrieve(request.user.subscription.stripe_subscription_id)
        stripe.Subscription.modify(subscription.id, cancel_at_period_end=True)
        free_plan = Plan.objects.get(id=3)
        request.user.subscription.plan = free_plan
        request.user.subscription.stripe_subscription_id = None
        request.user.subscription.current_period_end = subscription.current_period_end
        request.user.subscription.save()
        return redirect(reverse('account:manage_subscription') + '?recheck=true')
    except Exception:
        return redirect(reverse('account:manage_subscription'))

# Return subscription details as JSON
@login_required
def subscription(request):
    sub = request.user.subscription
    return JsonResponse({
        'plan_name': sub.plan.name.lower(),
        'stripe_subscription_id': sub.stripe_subscription_id,
        'hooks': sub.hooks,
        'merge_credits': sub.merge_credits,
        'current_period_end': sub.current_period_end
    })

# Send HTML email
def send_html_email2(subject, message, from_email, to_email, html_file, context):
    html_content = render_to_string(html_file, context)
    text_content = strip_tags(html_content)
    send_mail(subject, text_content, from_email, [to_email], html_message=html_content)

# Send confirmation email
def send_confirmation_email(email, name):
    logi_url = settings.DOMAIN + "login"
    name = name or "there"
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to HooksMaster.io</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto;">
    <h2 style="color: #2c3e50;">Hi {name},</h2>
<p>Welcome to <strong>HooksMaster.io</strong>! Your journey to creating high-converting video hooks effortlessly starts here. Your account has been successfully created, and you’re ready to optimize your ads.</p>

<h3 style="color: #2c3e50;">Next Steps:</h3>
<ul>
<li><strong>Log in:</strong> <a href="https://hooksmaster.io/login" style="color: #3498db;">Login to HooksMaster.io</a></li>
<li><strong>Get Started:</strong> Prepare your hooks and generate winning creatives.</li>
</ul>

<p>If you need support, we’re here to help. Feel free to reach out to us at <a href="mailto:support@hooksmaster.io" style="color: #3498db;">support@hooksmaster.io</a>.</p>

<p>Let’s create some high-converting hooks together!</p>

<a href="https://hooksmaster.io/login" style="display: inline-block; padding: 10px 20px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Login Now</a>

<p>Best regards,</p>
<p><strong>The HooksMaster.io Team</strong></p>
</div>
</body>
</html>
    """
    email_message = EmailMessage(subject="Welcome to HooksMaster.io – Your Account is Ready!", body=html_content, from_email=settings.EMAIL_HOST_USER, to=[email])
    email_message.content_subtype = "html"
    email_message.send(fail_silently=True)

# Log in the user
def _login(request, user):
    backend = "django.contrib.auth.backends.ModelBackend"
    user.backend = backend
    login(request, user, backend=backend)
