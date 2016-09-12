from django.views.decorators.csrf import csrf_exempt
from redis.exceptions import RedisError, DataError
from rest_framework import status
from rest_framework.parsers import JSONParser
from sds_controller.common_utils import  JSONResponse, get_redis_connection, get_project_list, is_valid_request


@csrf_exempt
def bw_list(request):
    """
    List all slas, or create a SLA.
    """ 
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED) 
              
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if request.method == 'GET':
        try:
            project_list = get_project_list(token)
            keys = r.keys('bw:AUTH_*')
        except:
            print "Error getting project list in bw_list"

        bw_limits = []        
        for it in keys:
            for key, value in r.hgetall(it).items():
                policy_name = r.hget('storage-policy:' + key, 'name')
                try:
                    bw_limits.append({'project_id': it.replace('bw:AUTH_', ''), 'project_name': project_list[it.replace('bw:AUTH_', '')], 'policy_id': key,
                                  'policy_name': policy_name, 'bandwidth': value})
                except Exception as e:
                    print "Error getting SLAs: "+str(e)               

        return JSONResponse(bw_limits, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            r.hmset('bw:AUTH_' + str(data['project_id']), {data['policy_id']: data['bandwidth']})
            return JSONResponse(data, status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse('Error saving SLA.', status=status.HTTP_400_BAD_REQUEST)
        
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
def bw_detail(request, project_key):
    """
    Retrieve, update or delete SLA.
    """
    token = is_valid_request(request)
    if not token:
        return JSONResponse('You must be authenticated as Crystal admin.', status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        r = get_redis_connection()
    except RedisError:
        return JSONResponse('Error connecting with DB', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    project_id = str(project_key).split(':')[0]
    policy_id = str(project_key).split(':')[1]

    if request.method == 'GET':

        try:
            project_list = get_project_list(token)
        except:
            print "Error getting project list in bw_details"

        bandwidth = r.hget('bw:AUTH_' + project_id, policy_id)
        policy_name = r.hget('storage-policy:' + policy_id, 'name')
        sla = {'id': project_key, 'project_id': project_id, 'project_name': project_list[project_id], 'policy_id': policy_id, 'policy_name': policy_name, 'bandwidth': bandwidth}
        return JSONResponse(sla, status=status.HTTP_200_OK)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        try:
            r.hmset('bw:AUTH_' + project_id, {policy_id: data['bandwidth']})
            return JSONResponse('Data updated', status=status.HTTP_201_CREATED)
        except DataError:
            return JSONResponse('Error updating data', status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        r.hdel('bw:AUTH_' + project_id, policy_id)
        return JSONResponse('SLA has been deleted', status=status.HTTP_204_NO_CONTENT)
    return JSONResponse('Method ' + str(request.method) + ' not allowed.', status=status.HTTP_405_METHOD_NOT_ALLOWED)
