from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User


class GoogleSuperuserAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to automatically grant superuser status to Google SSO users.
    This matches the behavior of the OTP login system.
    """
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed.
        """
        # Check if this is a new user
        if sociallogin.is_existing:
            # User already exists, make sure they're a superuser
            user = sociallogin.user
            if not user.is_superuser:
                user.is_superuser = True
                user.is_staff = True
                user.save()
        
    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly created social login user.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Make all Google SSO users superusers (matches OTP logic)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        
        return user
    
    def populate_user(self, request, sociallogin, data):
        """
        Hook for populating user instance with data from social account.
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Set superuser flags during user creation
        user.is_superuser = True
        user.is_staff = True
        
        return user
```

