import redis
import sys
import settings


def run():
    """
    When the controller is started (or restarted) all the actors
    are stopped, so we need to ensure the correct values in redis.
    """
    # Add source directories to sys path
    sys.path.insert(0, settings.CONTROLLERS_DIR)

    r = redis.Redis(connection_pool=settings.REDIS_CON_POOL)

    # Workload metric definitions
    for key in r.keys('workload_metric:*'):
        r.hset(key, 'status', 'Stopped')

    # Workload metric Actors
    for key in r.keys('metric:*'):
        r.delete(key)

    # Dynamic policies
    for key in r.keys('policy:*'):
        r.hset(key, 'status', 'Stopped')

    # Controller Instances
    for key in r.keys('controller_instance:*'):
        r.hset(key, 'status', 'Stopped')
