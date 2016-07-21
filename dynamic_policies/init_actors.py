from pyactive.controller import init_host, serve_forever, start_controller
import redis
import dsl_parser


def get_redis_connection():
    return redis.StrictRedis(host="localhost", port=6379, db=0)


def start_actors():
    r = get_redis_connection()

    for metric in r.keys("metric:*"):
        r.delete(metric)
    
    global host
    global metrics
    tcpconf = ('tcp', ('127.0.0.1', 6375))
    # momconf = ('mom',{'name':'metric_host','ip':'127.0.0.1','port':61613, 'namespace':'/topic/iostack'})
    host = init_host(tcpconf)
    metrics = {}
    metrics["get_ops_tenant"] = host.spawn_id("get_ops_tenant", 'metrics.swift_metric', 'SwiftMetric', ["amq.topic", "get_ops_tenant", "metrics.get_tenant"])
    metrics["put_ops_tenant"] = host.spawn_id("put_ops_tenant", 'metrics.swift_metric', 'SwiftMetric', ["amq.topic", "put_ops_tenant", "metrics.put_tenant"])
    
    metrics["active_get_requests"] = host.spawn_id("active_get_requests", 'metrics.swift_metric', 'SwiftMetric',
                                                   ["amq.topic", "active_get_requests", "metrics.active_get_requests"])
    metrics["active_put_requests"] = host.spawn_id("active_put_requests", 'metrics.swift_metric', 'SwiftMetric',
                                                   ["amq.topic", "active_put_requests", "metrics.active_put_requests"])

    # metrics["head_ops_tenant"] = host.spawn_id("head_ops_tenant", 'metrics.collectd_metric', 'CollectdMetric',
    #                                            ["amq.topic", "head_ops_tenant", "collectd.*.groupingtail.tm.*.head_ops.#"])
    metrics["get_bw"] = host.spawn_id("get_bw_tenant", 'metrics.swift_metric', 'SwiftMetric', ["amq.topic", "get_bw", "metrics.get_bw"])
    metrics["put_bw"] = host.spawn_id("put_bw_tenant", 'metrics.swift_metric', 'SwiftMetric', ["amq.topic", "put_bw", "metrics.put_bw"])
    
    metrics["get_ops_container"] = host.spawn_id("get_ops_container", 'metrics.swift_metric', 'SwiftMetric',
                                                 ["amq.topic", "get_ops_container", "metrics.get_container"])
    metrics["put_ops_container"] = host.spawn_id("put_ops_container", 'metrics.swift_metric', 'SwiftMetric',
                                                 ["amq.topic", "put_ops_container", "metrics.put_container"])

    # metrics["head_ops_container"] = host.spawn_id("head_ops_container", 'metrics.collectd_metric', 'CollectdMetric',
    #                                               ["amq.topic", "head_ops_container", "collectd.*.groupingtail.cm.*.head_ops.#"])
    # metrics["get_bw_container"] = host.spawn_id("get_bw_container", 'metrics.collectd_metric', 'CollectdMetric',
    #                                             ["amq.topic", "get_bw_container", "collectd.*.groupingtail.cm.*.get_bw.#"])
    # metrics["put_bw_container"] = host.spawn_id("put_bw_container", 'metrics.collectd_metric', 'CollectdMetric',
    #                                             ["amq.topic", "put_bw_container", "collectd.*.groupingtail.cm.*.put_bw.#"])
    
    # Metrics for Bandwidth differentiation
    metrics["get_bw_info"] = host.spawn_id("get_bw_info", 'metrics.bw_info', 'BwInfo', ["amq.topic", "get_bw_info", "bwdifferentiation.get_bw_info.#", "GET"])
    metrics["put_bw_info"] = host.spawn_id("put_bw_info", 'metrics.bw_info', 'BwInfo', ["amq.topic", "put_bw_info", "bwdifferentiation.put_bw_info.#", "PUT"])
    metrics["ssync_bw_info"] = host.spawn_id("ssync_bw_info", 'metrics.bw_info_ssync', 'BwInfoSSYNC',
                                             ["amq.topic", "ssync_bw_info", "bwdifferentiation.ssync_bw_info.#", "SSYNC"])
    
    try:
        for metric in metrics.values():
            metric.init_consum()
    except Exception as e:
        print e.args
        for metric in metrics.values():
            print 'metric!', metric
            metric.stop_actor()

    rules = {}
    # rules["get_bw"] = host.spawn_id("abstract_enforcement_algorithm_get", 'rules.min_slo_tenant_global_share_spare_bw', 'MinTenantSLOGlobalSpareBWShare',
    #                                 ["abstract_enforcement_algorithm_get","GET"])
    rules["get_bw"] = host.spawn_id("abstract_enforcement_algorithm_get", 'rules.simple_proportional_bandwidth', 'SimpleProportionalBandwidthPerTenant',
                                    ["abstract_enforcement_algorithm_get", "GET"])
    rules["get_bw"].run("get_bw_info")

    # rules["put_bw"] = host.spawn_id("abstract_enforcement_algorithm_put", 'rules.min_slo_tenant_global_share_spare_bw', 'MinTenantSLOGlobalSpareBWShare',
    #                                 ["abstract_enforcement_algorithm_put","PUT"])
    rules["put_bw"] = host.spawn_id("abstract_enforcement_algorithm_put", 'rules.simple_proportional_bandwidth', 'SimpleProportionalBandwidthPerTenant',
                                    ["abstract_enforcement_algorithm_put", "PUT"])
    rules["put_bw"].run("put_bw_info")
    
    rules["ssync_bw"] = host.spawn_id("abstract_enforcement_algorithm_ssync", 'rules.simple_proportional_replication_bandwidth',
                                      'SimpleProportionalReplicationBandwidth', ["abstract_enforcement_algorithm_ssync", "SSYNC"])
    rules["ssync_bw"].run("ssync_bw_info")
    
    start_redis_rules(host, rules)
    
    return host


def start_redis_rules(host, rules):
    # START DYNAMIC POLICIES STORED IN REDIS, IF ANY
    r = get_redis_connection()
    dynamic_policies = r.keys("policy:*")
    
    
    
    if dynamic_policies:
        print "\nStarting dynamic rules stored in redis:"
        
    for policy in dynamic_policies:
        policy_data = r.hgetall(policy)
        
        if policy_data['alive'] == 'True':
            _, rule_parsed = dsl_parser.parse(policy_data['policy_description']) 
            target = rule_parsed.target[0][1]  # Tenant ID or tenant+container
            for action_info in rule_parsed.action_list:
                if action_info.transient:
                    print 'Transient rule:', policy_data['policy_description']
                    rules[policy] = host.spawn_id(str(policy), 'rule_transient', 'TransientRule', [rule_parsed, action_info, target, host])
                    rules[policy].start_rule()
                else:
                    print 'Rule:', policy_data['policy_description']
                    rules[policy] = host.spawn_id(str(policy), 'rule', 'Rule', [rule_parsed, action_info, target, host])
                    rules[policy].start_rule()


def main():
    print "-- Starting workload metric actors --"
    start_controller('pyactive_thread')
    serve_forever(start_actors)

if __name__ == "__main__":
    main()
