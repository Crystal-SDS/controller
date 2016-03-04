from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser, FileUploadParser
from django.conf import settings
import redis
import json
from . import dsl_parser
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
from storlet.views import deploy, undeploy

host = None
remote_host = None

class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

def is_valid_request(request):
    headers = {}
    try:
        headers['X-Auth-Token'] = request.META['HTTP_X_AUTH_TOKEN']
        return headers
    except:
        return None

def get_redis_connection():
    return redis.Redis(connection_pool=settings.REDIS_CON_POOL)

#TODO: Improve the implementation to create the host connection
def create_host():
    start_controller("pyactive_thread")
    tcpconf = ('tcp', ('127.0.0.1', 9899))
    global host
    host = init_host(tcpconf)
    global remote_host
    remote_host = host.lookup(settings.PYACTIVE_URL+'controller/Host/0')

"""
Metric Workload part
"""
@csrf_exempt
def add_metric(request):
    """
    Add a metric workload in the registry (redis)
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("metric:*")
        print 'keys', keys
        metrics = []
        for key in keys:
            metric = r.hgetall(key)
            metric["name"]=key.split(":")[1]
            metrics.append(metric)
        return JSONResponse(metrics, status=200)
    if request.method == 'POST':
        data = JSONParser().parse(request)
        name = data.pop("name", None)
        if not name:
            return JSONResponse('Metric must have a name', status=400)
        r.hmset('metric:'+str(name), data)
        return JSONResponse('Metric has been added in the registy', status=201)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def metric_detail(request, name):
    """
    Get, update or delete a metric workload from the registry.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        metric = r.hgetall("metric:"+str(name))
        return JSONResponse(metric, status=200)

    if request.method == 'PUT':
        if not r.exists('metric:'+str(name)):
            return JSONResponse('Metric with name:  '+str(name)+' not exists.', status=404)

        data = JSONParser().parse(request)
        r.hmset('metric:'+str(name), data)
        return JSONResponse('The metadata of the metric workload with name: '+str(name)+' has been updated', status=201)

    if request.method == 'DELETE':
        r.delete("metric:"+str(id))
        return JSONResponse('Metric workload has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)


"""
Dynamic Filters part
"""
@csrf_exempt
def add_dynamic_filter(request):
    """
    Add a filter with its default parameters in the registry (redis). List all the dynamic filters registered.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'GET':
        keys = r.keys("filter:*")
        dynamic_filters = []
        for key in keys:
            dynamic_filter = r.hgetall(key)
            dynamic_filter["name"]=key.split(":")[1]
            dynamic_filters.append(dynamic_filter)
        return JSONResponse(dynamic_filters, status=200)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        name = data.pop("name", None)
        if not name:
            return JSONResponse('Filter must have a name', status=400)
        r.hmset('filter:'+str(name), data)
        return JSONResponse('Filter has been added in the registy', status=201)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def dynamic_filter_detail(request, name):
    """
    Get, update or delete a dynamic filter from the registry.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        dynamic_filter = r.hgetall("filter:"+str(name))
        return JSONResponse(dynamic_filter, status=200)

    if request.method == 'PUT':
        if not r.exists('filter:'+str(name)):
            return JSONResponse('Dynamic filter with name:  '+str(name)+' not exists.', status=404)
        data = JSONParser().parse(request)
        r.hmset('filter:'+str(name), data)
        return JSONResponse('The metadata of the dynamic filter with name: '+str(name)+' has been updated', status=201)

    if request.method == 'DELETE':
        r.delete("filter:"+str(name))
        return JSONResponse('Dynamic filter has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

"""
Storage nodes
"""
@csrf_exempt
def list_storage_node(request):
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == "GET":
        keys = r.keys("SN:*")
        print 'keys', keys
        storage_nodes = []
        for k in keys:
            sn = r.hgetall(k)
            sn["id"]=k.split(":")[1]
            storage_nodes.append(sn)
        return JSONResponse(storage_nodes, status=200)

    if request.method == "POST":
        sn_id = r.incr("storage_nodes:id")
        data = JSONParser().parse(request)
        r.hmset('SN:'+str(sn_id), data)
        return JSONResponse('Tenants group has been added in the registy', status=201)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

"""
Tenants group part
"""
@csrf_exempt
def add_tenants_group(request):
    """
    Add a filter with its default parameters in the registry (redis). List all the tenants groups saved in the registry.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("G:*")
        gtenants = {}
        for key in keys:
            gtenant = r.lrange(key, 0, -1)
            gtenants[key] = gtenant
            #gtenants.extend(eval(gtenant[0]))
        return JSONResponse(gtenants, status=200)

    if request.method == 'POST':
        gtenant_id = r.incr("gtenant:id")
        data = JSONParser().parse(request)
        r.lpush('G:'+str(gtenant_id), *data)
        return JSONResponse('Tenants group has been added in the registy', status=201)

    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def tenants_group_detail(request, gtenant_id):
    """
    Get, update or delete a tenants group from the registry.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        gtenant = r.lrange("G:"+str(gtenant_id), 0, -1)
        # r.hgetall("gtenants:"+str(gtenant_id))
        return JSONResponse(gtenant, status=200)

    if request.method == 'PUT':
        if not r.exists('G:'+str(gtenant_id)):
            return JSONResponse('The members of the tenants group with id:  '+str(gtenant_id)+' not exists.', status=404)
        data = JSONParser().parse(request)
        #for tenant in data:
        r.lpush('G:'+str(gtenant_id), *data)
        return JSONResponse('The members of the tenants group with id: '+str(gtenant_id)+' has been updated', status=201)

    if request.method == 'DELETE':
        r.delete("G:"+str(gtenant_id))
        return JSONResponse('Tenants grpup has been deleted', status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def gtenants_tenant_detail(request, gtenant_id, tenant_id):
    """
    Delete a member from a tenants group.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)
    if request.method == 'DELETE':
        r.lrem("G:"+str(gtenant_id), str(tenant_id), 1)
        return JSONResponse('Tenant'+str(tenant_id)+'has been deleted from group with the id: '+str(gtenant_id), status=204)
    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

@csrf_exempt
def policy_list(request):
    """
    List all policies. Deploy new policies.
    """
    try:
        r = get_redis_connection()
    except:
        return JSONResponse('Error connecting with DB', status=500)

    if request.method == 'GET':
        keys = r.keys("policy:*")
        policies = []
        for key in keys:
            policy = r.hgetall(key)
            policies.append(policy)
        return JSONResponse(policies, status=200)

    if request.method == 'POST':
        headers = is_valid_request(request)
        if not headers:
            return JSONResponse('You must be authenticated. You can authenticate yourself  with the header X-Auth-Token ', status=401)
        rules_string = request.body.splitlines()
        parsed_rules = []
        for rule in rules_string:
            """
            Rules improved:
            TODO: Handle the new parameters of the rule
            Add containers and object in rules
            Add execution server in rules
            Add object type in rules
            """
            try:
                condition_list, rule_parsed = dsl_parser.parse(rule)

                if condition_list:
                    parsed_rules.append(rule_parsed)
                else:
                    print 'rule_parsed', rule_parsed
                    response = do_action(request, r, rule_parsed, headers)
                    print "pepito", response
            except Exception as e:
                print "The rule: "+rule+" cannot be parsed"
                print "Exception message", e
                return JSONResponse("Error in rule: "+rule+" Error message --> "+str(e), status=401)
        deploy_policy(r, parsed_rules)
        # launch(deploy_policy, [r, parsed_rules])
        return JSONResponse('Policies added successfully!', status=201)

    return JSONResponse('Method '+str(request.method)+' not allowed.', status=405)

def do_action(request, r, rule_parsed, headers):

    for target in rule_parsed.target:
        for action_info in rule_parsed.action_list:

            dynamic_filter = r.hgetall("filter:"+str(action_info.filter))
            storlet = r.hgetall("storlet:"+dynamic_filter["identifier"])

            if not storlet:
                resonse = JSONResponse('Filter does not exists', status=404)
                break

            if action_info.action == "SET":
                #TODO: What happends if any of each parameters are None or ''? Review the default parameters.
                prams = {"params":action_info.params, "execution_server":action_info.execution_server, "target_objects":rule_parsed.object_list}
                #TODO Review if this tenant has already deployed this filter. Not deploy the same filter more than one time.
                response = deploy(r, storlet, target[1], params, headers)
            elif raction_info.action == "DELETE":
                response = undeploy(r, storlet, target[1], headers)

    return response

def deploy_policy(r, parsed_rules):
    # self.aref = 'atom://' + self.dispatcher.name + '/controller/Host/0'
    rules = {}
    cont = 0
    if not host or not remote_host:
        create_host()
    for rule in parsed_rules:
        rules_to_parse = {}
        for tenant in rule.subject:
            rules_to_parse[tenant] = rule
        for key in rules_to_parse.keys():
            policy_id = r.incr("policies:id")
            rules[cont] = remote_host.spawn_id(str(policy_id), 'rule', 'Rule', [rules_to_parse[key], key, remote_host, settings.PYACTIVE_IP, settings.PYACTIVE_PORT, settings.PYACTIVE_TRANSPORT])
            rules[cont].start_rule()
            #Add policy into redis
            r.hmset('policy:'+str(policy_id), {"id":policy_id, "policy_description":rule, "policy_location":settings.PYACTIVE_URL+"/rule/Rule/"+str(policy_id), "alive":True})
            cont += 1
