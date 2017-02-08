import json
import logging
import mimetypes
import os

from django.conf import settings
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.views import APIView
from eventlet import sleep

from api.common_utils import JSONResponse, get_redis_connection, get_project_list, to_json_bools, create_local_host
from filters.views import save_file, make_sure_path_exists

# logger = logging.getLogger(__name__)
#
# controller_actors = dict()
# metric_actors = dict()



