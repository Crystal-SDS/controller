import logging
import subprocess
import json
import os
import re

from api.exceptions import AnalyticsJobSubmissionException
from api.common import get_redis_connection

from django.conf import settings
from StringIO import StringIO
from subprocess import PIPE, STDOUT, Popen

logger = logging.getLogger(__name__)


def execute_java_analyzer(path_to_jar, path_to_job_file):
    p = Popen(['java', '-jar', path_to_jar, path_to_job_file], stdout=PIPE, stderr=STDOUT)
    json_result = ''

    for line in p.stdout:
        if line.startswith("{\"original-job-code\":"):
            json_result += line

    io = StringIO(json_result)
    return json.load(io)


def get_lambda_pushdown_policy(target_id):
    r = get_redis_connection()

    lambda_policy_id = None

    pipeline = r.hgetall("pipeline:" + target_id)
    if pipeline:
        # for each policy in the pipeline
        for policy_id, json_encoded_policy in pipeline.items():
            policy_dict = json.loads(json_encoded_policy)

            if policy_dict['filter_name'] == settings.JOB_ANALYZER_LAMBDA_PUSHDOWN_FILTER:
                lambda_policy_id = policy_id
                # We assume that a single tenant/container only has one pushdown filter
                break

    return lambda_policy_id


def update_lambda_params(target_id, policy_id, lambdas_to_migrate):
    r = get_redis_connection()

    logger.debug("Lambdas to migrate:" + str(lambdas_to_migrate) + " for target: " + str(target_id))
    lambdas_as_string = ''
    index = 0
    for x in lambdas_to_migrate:
        lambdas_as_string += str(index) + "-lambda=" + str(x['lambda-type-and-body']) + ","
        index += 1

    policy_redis = r.hget("pipeline:" + str(target_id), policy_id)
    json_data = json.loads(policy_redis)
    json_data.update({'params': lambdas_as_string[:-1]})
    r.hset("pipeline:" + str(target_id), policy_id, json.dumps(json_data))


def init_job_submission(job_execution_data):

    r = get_redis_connection()

    job_name = job_execution_data['_simple_name']
    job_migratory_name = job_execution_data['name']

    # STEP 1: Execute the JobAnalyzer
    analyzer_data = r.hgetall('analyzer:' + str(job_execution_data['analyzer_id']))
    analyzer_file_name = analyzer_data['analyzer_file_name']
    analyzer_framework = analyzer_data['framework']
    job_analyzer_path = os.path.join(settings.ANALYZERS_DIR, str(analyzer_file_name))
    job_path = os.path.join(settings.JOBS_DIR, str(job_execution_data['job_file_name']))

    json_object = execute_java_analyzer(job_analyzer_path, job_path)

    # STEP 2: Get the lambdas and the code of the Job
    lambdas_to_migrate = json_object.get("lambdas")
    original_job_code = json_object.get("original-job-code")
    pushdown_job_code = json_object.get("pushdown-job-code")

    # STEP 3: Decide whether or not to execute the lambda pushdown
    pushdown = job_execution_data['pushdown']
    job_to_compile = original_job_code

    # STEP 4: Set the lambdas in the storlet policy if necessary
    if pushdown:
        policies_to_update = []
        # Check all containers have a lambdapushdown policy assigned
        for container in lambdas_to_migrate:
            target_id = str(job_execution_data['tenant_id']) + ':' + container
            policy_id = get_lambda_pushdown_policy(target_id)
            if not policy_id:
                raise AnalyticsJobSubmissionException("Container " + container + " does not have a lambdapushdown filter assigned")
            else:
                policies_to_update.append((target_id, container, policy_id))
        # Set lambdas to the policies
        for target_id, container, policy_id in policies_to_update:
            update_lambda_params(target_id, policy_id, lambdas_to_migrate.get(container))
        job_to_compile = pushdown_job_code
    else:
        for container in lambdas_to_migrate:
            target_id = str(job_execution_data['tenant_id']) + ':' + container
            policy_id = get_lambda_pushdown_policy(target_id)
            if policy_id:
                # Remove lambda params
                update_lambda_params(target_id, policy_id, '')

    # STEP 5: Compile pushdown/original job
    executor_location = settings.JOB_ANALYZER_EXECUTOR_LOCATION
    m = re.search('package\s*(\w\.?)*\s*;', job_to_compile)
    job_to_compile = job_to_compile.replace(m.group(0),
                                            'package ' + executor_location.replace('/', '.')[1:-1] + ';')
    job_to_compile = job_to_compile.replace(job_name, job_migratory_name)

    jobfile = open(executor_location + '/' + job_migratory_name + '.java', 'w')
    print >> jobfile, job_to_compile
    jobfile.close()

    logger.info("Starting compilation")
    if analyzer_framework == 'Spark':
        framework_libs_location = settings.JOB_ANALYZER_SPARK_LIBS_LOCATION
    elif analyzer_framework == 'Flink':
        framework_libs_location = settings.JOB_ANALYZER_FLINK_LIBS_LOCATION
    cmd = settings.JOB_ANALYZER_JAVAC_PATH + ' -cp \"' + framework_libs_location + '*\" '
    cmd += executor_location + job_migratory_name + '.java'
    logger.info(">> EXECUTING: " + cmd)
    proc = subprocess.call(cmd, shell=True)
    if proc != 0:
        raise AnalyticsJobSubmissionException("javac error compiling " + job_migratory_name)

    # STEP 6: Package the Job class as a JAR and set the manifest
    logger.info("Starting packaging")
    cmd = 'jar -cfe ' + executor_location + job_migratory_name + '.jar ' + \
          executor_location.replace('/', '.')[1:] + job_migratory_name + ' ' + \
          executor_location + job_migratory_name + '.class'
    logger.info(">> EXECUTING: " + cmd)
    proc = subprocess.call(cmd, shell=True)
    if proc != 0:
        raise AnalyticsJobSubmissionException("jar error packaging " + job_migratory_name)

    # STEP 7: In cluster mode, we need to store the produced jar in HDFS to make it available to workers
    if settings.JOB_ANALYZER_CLUSTER_MODE:
        logger.info("Starting to store the JAR in HDFS")
        cmd = settings.JOB_ANALYZER_HDFS_LOCATION + ' -put -f ' + executor_location + job_migratory_name + '.jar ' + \
              ' /' + job_migratory_name + '.jar'
        logger.info(">> EXECUTING: " + cmd)
        proc = subprocess.call(cmd, shell=True)
        if proc != 0:
            raise AnalyticsJobSubmissionException("There was a problem storing the " + job_migratory_name + " JAR in HDFS")

    # STEP 8: Execute the job against Swift
    logger.info("Starting execution")
    if settings.JOB_ANALYZER_CLUSTER_MODE:
        deploy_mode = 'cluster'
        jar_location = 'hdfs://' + settings.JOB_ANALYZER_HDFS_IP_PORT + '/' + job_migratory_name + '.jar'
    else:
        deploy_mode = 'client'
        jar_location = executor_location + job_migratory_name + '.jar'

    if analyzer_framework == 'Spark':
        executor_cores = job_execution_data['executor_cores'] or settings.JOB_ANALYZER_AVAILABLE_CPUS
        executor_memory = job_execution_data['executor_memory'] or settings.JOB_ANALYZER_AVAILABLE_RAM
        cmd = 'bash ' + settings.JOB_ANALYZER_SPARK_FOLDER + 'bin/spark-submit --deploy-mode ' + deploy_mode + \
              ' --master ' + settings.JOB_ANALYZER_SPARK_MASTER_URL + ' ' + \
              '--class ' + executor_location.replace('/', '.')[1:] + job_migratory_name + ' ' + \
              '--driver-class-path ' + settings.JOB_ANALYZER_SPARK_FOLDER + 'jars/stocator-1.0.9.jar ' + \
              '--executor-cores ' + executor_cores + ' --executor-memory ' + executor_memory + \
              ' ' + jar_location + ' --jars ' + settings.JOB_ANALYZER_SPARK_FOLDER + 'jars/*.jar'
        # Note: to use FlightRecorderTaskMetrics, add the following line to spark submit call:
        # '--conf spark.extraListeners=ch.cern.sparkmeasure.FlightRecorderStageMetrics,ch.cern.sparkmeasure.FlightRecorderTaskMetrics ' +
    elif analyzer_framework == 'Flink':
        parallelism = '-p ' + job_execution_data['parallelism'] or ''
        cmd = 'bash ' + settings.JOB_ANALYZER_FLINK_FOLDER + 'bin/flink run ' + parallelism + ' ' + jar_location

    logger.info(">> EXECUTING: " + cmd)
    Popen(cmd, shell=True)

    # STEP 9: Clean files
    os.remove(executor_location + job_migratory_name + '.java')
    os.remove(executor_location + job_migratory_name + '.class')
    os.remove(executor_location + job_name + 'Java8Translated.java')
    # os.remove(executor_location + job_migratory_name + '.jar')

    r.hset('job_execution:' + str(job_execution_data['id']), 'status', 'submitted')
