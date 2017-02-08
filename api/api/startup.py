from api.common_utils import get_redis_connection
import sys
import settings

def run():
    """
    When the controller is started (or restarted) all the actors
    are stopped, so we need to ensure the correct values in redis.
    """

    # Add source directories to sys path
    sys.path.insert(0, settings.GLOBAL_CONTROLLERS_DIR)

    r = get_redis_connection()

    # Workload metric definitions
    for key in r.keys('workload_metric:*'):
        r.hset(key, 'enabled', False)

    # Workload metric Actors
    for key in r.keys('metric:*'):
        r.delete(key)

    # Dynamic policies
    for key in r.keys('policy:*'):
        r.hset(key, 'alive', 'False')

    # Global controllers
    for key in r.keys('controller:*'):
        r.hset(key, 'enabled', 'False')
