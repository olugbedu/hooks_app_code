from django.contrib.auth import get_user_model

# Get the user model
User = get_user_model()

class EmailAuthBackend:
    """
    Authenticate using an e-mail address.
    """
    def authenticate(self, request, username=None, password=None):
        """
        Authenticate the user based on email and password.
        """
        try:
            # Try to get the user by email
            user = User.objects.get(email=username)
            # Check if the password is correct
            if user.check_password(password):
                return user
            return None
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            # Return None if user does not exist or multiple users found
            return None

    def get_user(self, user_id):
        """
        Get the user by their ID.
        """
        try:
            # Try to get the user by primary key (ID)
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            # Return None if user does not exist
            return None
