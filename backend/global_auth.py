from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.contrib.auth import get_user_model
import os

User = get_user_model()


class GlobalAPITokenAuthentication(BaseAuthentication):
    """
    Authenticate requests using a single token provided in the
    Authorization header as: "Authorization: Token <token>".

    The valid token is read from the environment variable
    GLOBAL_API_TOKEN. When a matching token is presented, the
    backend will authenticate the request as a dedicated user
    (created on-demand) whose username is taken from
    GLOBAL_API_USERNAME (defaults to 'global_api_user').

    This is a convenience/backdoor for machines (or the frontend)
    when you want to use one static token across the deployment.
    Use with caution: treat the token as a secret and rotate it
    regularly.
    """

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2:
            return None

        scheme, token = parts[0], parts[1]
        if scheme.lower() != 'token':
            return None

        env_token = os.environ.get('GLOBAL_API_TOKEN')
        if not env_token:
            # No global token configured; skip this authenticator
            return None

        if token != env_token:
            raise exceptions.AuthenticationFailed('Invalid global API token')

        username = os.environ.get('GLOBAL_API_USERNAME', 'global_api_user')
        # Create or get a service account-like user. Keep it inactive
        # if you want to restrict Django admin access separately.
        user, created = User.objects.get_or_create(username=username, defaults={'is_active': True})
        return (user, None)

    def authenticate_header(self, request):
        return 'Token'
