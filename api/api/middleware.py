import logging
from datetime import datetime

from keystoneauth1 import exceptions
from rest_framework import status

from api.common_utils import JSONResponse, get_keystone_admin_auth

logger = logging.getLogger(__name__)

valid_tokens = dict()


class CrystalMiddleware:
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
        now = datetime.utcnow()

        if token not in valid_tokens:
            keystone = get_keystone_admin_auth()

            try:
                token_data = keystone.tokens.validate(token)
            except exceptions.base.ClientException:
                return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)

            token_expiration = datetime.strptime(token_data.expires, '%Y-%m-%dT%H:%M:%SZ')

            token_roles = token_data.user['roles']
            for role in token_roles:
                if role['name'] == 'admin':
                    is_admin = True

            if token_expiration > now and is_admin:
                valid_tokens[token] = token_expiration
                return None

        else:
            token_expiration = valid_tokens[token]
            if token_expiration > now:
                return None
            else:
                valid_tokens.pop(token, None)

        return JSONResponse('You must be authenticated as admin.', status=status.HTTP_401_UNAUTHORIZED)
