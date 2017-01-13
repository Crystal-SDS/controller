from api.common_utils import get_redis_connection


def run():
    """
    When the controller is started (or restarted) all the actors
    are stopped, so we need to ensure the correct values in redis.
    """
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
