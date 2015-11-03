from metric import Througput
from rule import Rule
import rules_parse as p
import time
import operator

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

t = Througput("througput")
r = p.parse("FOR 2312 WHEN slowdown > 3 DO compress")
print r.asList()
rule = Rule(r)
print 'rule created'
print 'rule', rule.tenant
t.attach(rule)
time.sleep(10)
t.stop_consuming()
