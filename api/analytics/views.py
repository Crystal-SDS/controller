import datetime
import json
import logging
import mimetypes
import os
import sys

from django.conf import settings
from wsgiref.util import FileWrapper
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from operator import itemgetter
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.views import APIView

from api.common import JSONResponse, get_redis_connection
from api.exceptions import AnalyticsJobSubmissionException
from filters.views import save_file, make_sure_path_exists
from analytics.job_analyzer_executor import init_job_submission

logger = logging.getLogger(__name__)


@csrf_exempt
def job_history_list(request):
    """
    List all job history
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys('job_execution:*')
        history_list = []
        for key in keys:
            job_execution = r.hgetall(key)
            history_list.append(job_execution)
        sorted_list = sorted(history_list, key=lambda x: int(itemgetter('id')(x)), reverse=True)
        return JSONResponse(sorted_list, status=status.HTTP_200_OK)
    elif request.method == 'DELETE':
        keys = r.keys('job_execution:*')

        # 1st) delete files
        for key in keys:
            job_path = os.path.join(settings.JOBS_DIR,
                                    str(r.hget(key, 'job_file_name')))
            if os.path.exists(job_path):
                os.remove(job_path)

        # 2nd) delete Redis registers
        for key in keys:
            r.delete(key)
        r.delete('job_executions:id')

        return JSONResponse('Analyzer has been deleted', status=status.HTTP_204_NO_CONTENT)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


class JobSubmitData(APIView):
    """
    Submit a job.
    """
    parser_classes = (MultiPartParser, FormParser,)

    def post(self, request):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=500)

        data = json.loads(request.POST['metadata'])  # json data is in metadata parameter for this request
        if not data:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        job_execution_id = r.incr("job_executions:id")
        try:
            data['id'] = job_execution_id

            file_obj = request.FILES['file']

            make_sure_path_exists(settings.JOBS_DIR)
            path = save_file(file_obj, settings.JOBS_DIR)
            data['job_file_name'] = os.path.basename(path)
            data['_simple_name'] = path[path.rfind('/') + 1:path.rfind('.')]
            data['name'] = data['_simple_name'] + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

            data['status'] = '-'
            data['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            r.hmset('job_execution:' + str(job_execution_id), data)

            init_job_submission(data)

            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except AnalyticsJobSubmissionException as ajse:
            r.hset('job_execution:' + str(job_execution_id), 'status', 'submission failed')
            return JSONResponse(ajse.message, status=status.HTTP_400_BAD_REQUEST)
        except DataError:
            return JSONResponse("Error to save the object", status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            print sys.exc_info()
            return JSONResponse("Error uploading file", status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
def analyzer_list(request):
    """
    List all analyzers
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        keys = r.keys('analyzer:*')
        analyzers_list = []
        for key in keys:
            analyzer = r.hgetall(key)
            #to_json_bools(analyzer, 'enabled')
            analyzers_list.append(analyzer)
        return JSONResponse(analyzers_list, status=status.HTTP_200_OK)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def analyzer_detail(request, analyzer_id):
    """
    Retrieve, update or delete an analyzer.
    """
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        analyzer = r.hgetall('analyzer:' + str(analyzer_id))
        #to_json_bools(analyzer, 'enabled')
        return JSONResponse(analyzer, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('analyzer:' + str(analyzer_id), data)
            #analyzer_data = r.hgetall('analyzer:' + str(analyzer_id))
            #to_json_bools(analyzer_data, 'enabled')
            return JSONResponse("Data updated", status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse("Error updating data", status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # 1st) delete file
        if r.exists('analyzer:' + str(analyzer_id)):
            analyzer_path = os.path.join(settings.ANALYZERS_DIR,
                                         str(r.hget('analyzer:' + str(analyzer_id), 'analyzer_file_name')))
            if os.path.exists(analyzer_path):
                os.remove(analyzer_path)

        # 2nd) delete Redis register
        r.delete("analyzer:" + str(analyzer_id))

        # 3rd) If this is the last analyzer, the counter is reset
        keys = r.keys('analyzer:*')
        if not keys:
            r.delete('analyzers:id')

        return JSONResponse('Analyzer has been deleted', status=status.HTTP_204_NO_CONTENT)

    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


class AnalyzerData(APIView):
    """
    Upload or download an analyzer.
    """
    parser_classes = (MultiPartParser, FormParser,)

    def post(self, request):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=500)

        data = json.loads(request.POST['metadata'])  # json data is in metadata parameter for this request
        if not data:
            return JSONResponse("Invalid format or empty request", status=status.HTTP_400_BAD_REQUEST)

        analyzer_id = r.incr("analyzers:id")
        try:
            data['id'] = analyzer_id

            file_obj = request.FILES['file']

            make_sure_path_exists(settings.ANALYZERS_DIR)
            path = save_file(file_obj, settings.ANALYZERS_DIR)
            data['analyzer_file_name'] = os.path.basename(path)

            r.hmset('analyzer:' + str(analyzer_id), data)

            return JSONResponse(data, status=status.HTTP_201_CREATED)

        except DataError:
            return JSONResponse("Error saving the object", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print e
            return JSONResponse("Error uploading file", status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, analyzer_id):
        try:
            r = get_redis_connection()
        except RedisError:
            return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if r.exists('analyzer:' + str(analyzer_id)):
            analyzer_path = os.path.join(settings.ANALYZERS_DIR,
                                                  str(r.hget('analyzer:' + str(analyzer_id), 'analyzer_file_name')))
            if os.path.exists(analyzer_path):
                analyzer_name = os.path.basename(analyzer_path)
                analyzer_size = os.stat(analyzer_path).st_size

                # Generate response
                response = StreamingHttpResponse(FileWrapper(open(analyzer_path), analyzer_size),
                                                 content_type=mimetypes.guess_type(analyzer_path)[0])
                response['Content-Length'] = analyzer_size
                response['Content-Disposition'] = "attachment; filename=%s" % analyzer_name

                return response
            else:
                return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        else:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)
