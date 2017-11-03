import logging
from keystoneauth1 import exceptions
from rest_framework import status
from django.utils import timezone
from api.common import JSONResponse, get_keystone_admin_auth

logger = logging.getLogger(__name__)

valid_tokens = dict()


class CrystalMiddleware(object):
    def __init__(self):
        pass

    @staticmethod
    def process_request(request):

        # Example of the django logging
        # logger.info('Remote address: ' + str(request.META['REMOTE_ADDR']))
        # logger.info('User agent: ' + str(request.META['HTTP_USER_AGENT']))
        # logger.info('X-Auth-Token: ' + str(request.META['HTTP_X_AUTH_TOKEN']))

        if 'HTTP_X_AUTH_TOKEN' in request.META:
            token = request.META['HTTP_X_AUTH_TOKEN']
        else:
            return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

        is_admin = False
        now = timezone.now()

        if token not in valid_tokens:
            keystone_client = get_keystone_admin_auth()

            try:
                token_data = keystone_client.tokens.validate(token)
            except exceptions.base.ClientException:
                return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

            for role in token_data['roles']:
                if role['name'] == 'admin':
                    is_admin = True

            if token_data.expires > now and is_admin:
                valid_tokens[token] = token_data.expires
                return None

        else:
            token_expiration = valid_tokens[token]
            if token_expiration > now:
                return None
            else:
                valid_tokens.pop(token, None)

        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)
