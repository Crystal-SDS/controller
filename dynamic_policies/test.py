import sys
import os.path

from metrics.througput import Througput
from metrics.slowdown import Slowdown
from rule import Rule
import dsl_parser as p
import time
import operator
from pyactive.controller import init_host, serve_forever, start_controller, interval, sleep
from pyactive.exception import TimeoutError, PyactiveError
import requests
import json



# lists = [{"tenant_id":123, "througput":1}, {"tenant_id":3, "througput":1}, {"tenant_id":2, "througput":1},]
# json_lists = json.dumps(lists)
#
# print json_lists
#
# pepito = json.loads(lists)
# for p in pepito:
#     if p["tenant_id"] == 2:
#
# print operator.gt(10, 15)
# print operator.gt(5, 5)
# print operator.gt(10, 3)

# t = Througput("througput")
# s = Slowdown("slowdown")
# # r = p.parse("FOR 2312 WHEN slowdown > 3 DO compress")
# r = p.parse("FOR 2312 WHEN througput < 3 OR slowdown == 1 AND througput == 5 OR througput == 6 DO action")
#
# print r.asList()
# rule = Rule(r)
# print 'rule created'
# print 'rule', rule.tenant
# t.attach(rule)
# s.attach(rule)
# time.sleep(40)
# t.stop_consuming()

def start_test():
    tcpconf = ('tcp', ('127.0.0.1', 6375))
    host = init_host(tcpconf)
    metrics = {}
    metrics["througput"] = host.spawn_id("througput", 'metrics.througput', 'Througput', ["througput", host])
    metrics["slowdown"] = host.spawn_id("slowdown", 'metrics.slowdown', 'Slowdown', ["slowdown", host])

    metrics["througput"].init_consum()
    metrics["slowdown"].init_consum()
    # rules = {}
    # rules_string = """\
    # FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN througput < 3 OR slowdown == 1 AND througput == 5 OR througput == 6 DO SET 1 WITH param1=2
    # FOR 2312 WHEN througput > 3 AND slowdown >= 1 DO SET storlet WITH param1=2
    # FOR 2321 WHEN slowdown < 40 DO SET storlet WITH param1=2
    # FOR 2312 AND 2321 WHEN througput > 20 AND througput < 40 DO SET storlet WITH param1=2
    # FOR 2321 WHEN througput > 15.5 AND througput < 16 DO SET storlet WITH param1=2
    # FOR 2312 WHEN slowdown < 3 AND slowdown > 1 DO SET storlet WITH param1=2""".splitlines()
    #
    # rules_string = ["FOR 4f0279da74ef4584a29dc72c835fe2c9 WHEN througput < 3 OR slowdown == 1 AND througput == 5 OR througput == 6 DO SET 1 WITH param1=2"]
    # cont = 0
    #
    # for rule in rules_string:
    #     rules_to_parse = {}
    #     parsed_rule = p.parse(rule)
    #     print parsed_rule.tenants
    #     for tenant in parsed_rule.tenants:
    #         print 'tenant', tenant
    #         rules_to_parse[tenant] = parsed_rule
    #
    #
    #     for key in rules_to_parse.keys():
    #         print 'rule ', key
    #         rules[cont] =  host.spawn_id(str(cont), 'rule', 'Rule', [rules_to_parse[key], key, host, '127.0.0.1', 6375, 'tcp'])
    #         rules[cont].start_rule()
    #         cont += 1
    #
    #
    #     # metrics["througput"].attach(rules[0])
    #     # metrics["slowdown"].attach(rules[0])


def main():
    start_controller('pyactive_thread')
    serve_forever(start_test)
def main2():
    # export TOKEN=$(curl -d '{"auth":{"tenantName": "service", "passwordCredentials": {"username": "swift", "password": "urv"}}}' -H "Content-type: application/json" http://swift_mdw:5000/v2.0/tokens -s | jq '.access.token.id' | tr -d '"')
    data = {'auth':{'tenantName': 'service', 'passwordCredentials': {'username': 'swift', 'password': 'urv'}}}

    headers={"Content-type":"application/json"}
    resp = requests.get("http://10.30.235.235:5000/v2.0/tokens", data=json.dumps(data), headers=headers)
    print resp

if __name__ == "__main__":
    main()
