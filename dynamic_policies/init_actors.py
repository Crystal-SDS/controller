from pyactive.controller import init_host, serve_forever, start_controller

def start_test():
    global host
    global metrics
    tcpconf = ('tcp', ('127.0.0.1', 6375))
    #momconf = ('mom',{'name':'metric_host','ip':'127.0.0.1','port':61613, 'namespace':'/topic/iostack'})
    host = init_host(tcpconf)
    metrics = {}
    metrics["get_ops_tenant"] = host.spawn_id("get_ops_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "get_ops_tenant", "collectd.*.groupingtail.tm.*.get_ops.#"])
    metrics["put_ops_tenant"] = host.spawn_id("put_ops_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "put_ops_tenant", "collectd.*.groupingtail.tm.*.put_ops.#"])
    metrics["head_ops_tenant"] = host.spawn_id("head_ops_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "head_ops_tenant", "collectd.*.groupingtail.tm.*.head_ops.#"])
    metrics["get_bw_tenant"] = host.spawn_id("get_bw_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "get_bw_tenant", "collectd.*.groupingtail.tm.*.get_bw.#"])
    metrics["put_bw_tenant"] = host.spawn_id("put_bw_tenant", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "put_bw_tenant", "collectd.*.groupingtail.tm.*.put_bw.#"])
    metrics["get_ops_container"] = host.spawn_id("get_ops_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "get_ops_container", "collectd.*.groupingtail.cm.*.get_ops.#"])
    metrics["put_ops_container"] = host.spawn_id("put_ops_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "put_ops_container", "collectd.*.groupingtail.cm.*.put_ops.#"])
    metrics["head_ops_container"] = host.spawn_id("head_ops_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "head_ops_container", "collectd.*.groupingtail.cm.*.head_ops.#"])
    metrics["get_bw_container"] = host.spawn_id("get_bw_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "get_bw_container", "collectd.*.groupingtail.cm.*.get_bw.#"])
    metrics["put_bw_container"] = host.spawn_id("put_bw_container", 'metrics.collectd_metric', 'CollectdMetric', ["amq.topic", "put_bw_container", "collectd.*.groupingtail.cm.*.put_bw.#"])
    metrics["get_bw_info"] = host.spawn_id("get_bw_info", 'metrics.bw_info', 'BwInfo', ["amq.topic","get_bw_info", "bwdifferentiation.get_bw_info.#","get_bw_info","GET"])
    metrics["put_bw_info"] = host.spawn_id("put_bw_info", 'metrics.bw_info', 'BwInfo', ["amq.topic","put_bw_info", "bwdifferentiation.put_bw_info.#","put_bw_info","PUT"])
    metrics["ssync_bw_info"] = host.spawn_id("ssync_bw_info", 'metrics.bw_info_ssync', 'BwInfoSSYNC', ["amq.topic","ssync_bw_info", "bwdifferentiation.ssync_bw_info.#","ssync_bw_info","SSYNC"])
    
    try:
        for metric in metrics.values():
            metric.init_consum()
    except Exception as e:
        print e.args
        for metric in metrics.values():
            print 'metric!', metric
            metric.stop_actor()
    
    rules = {}
    rules["get_bw"] = host.spawn_id("abstract_enforcement_algorithm_get", 'rules.min_bandwidth_per_tenant', 'SimpleMinBandwidthPerTenant', ["abstract_enforcement_algorithm_get","GET"])
    rules["get_bw"].run("get_bw_info")

    rules["put_bw"] = host.spawn_id("abstract_enforcement_algorithm_put", 'rules.min_bandwidth_per_tenant', 'SimpleMinBandwidthPerTenant', ["abstract_enforcement_algorithm_put","PUT"])
    rules["put_bw"].run("put_bw_info")
    
    rules["ssync_bw"] = host.spawn_id("abstract_enforcement_algorithm_ssync", 'rules.simple_proportional_replication_bandwidth', 'SimpleProportionalReplicationBandwidth', ["abstract_enforcement_algorithm_ssync","SSYNC"])
    rules["ssync_bw"].run("ssync_bw_info")
    
def main():
    print "-- Starting workload metric actors --"
    start_controller('pyactive_thread')
    serve_forever(start_test)

if __name__ == "__main__":
    main()
    