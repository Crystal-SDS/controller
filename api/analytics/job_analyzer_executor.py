import logging
import subprocess
import time
import json
import os
import re

from api.exceptions import AnalyticsJobSubmissionException
from api.common_utils import get_redis_connection

from django.conf import settings
from StringIO import StringIO
from subprocess import PIPE, STDOUT, Popen

logger = logging.getLogger(__name__)


def executeJavaAnalyzer(pathToJAR, pathToJobFile):
    p = Popen(['java', '-jar', pathToJAR, pathToJobFile], stdout=PIPE, stderr=STDOUT)
    jsonResult = ''

    json_output = False
    for line in p.stdout:
        if line.startswith("{\"original-job-code\":"): json_output = True
        if (json_output): jsonResult += line

    io = StringIO(jsonResult)
    return json.load(io)


def get_current_lambda_pushdown_policy(tenant_id, container_id):
    r = get_redis_connection()

    # Trying 1st the target with tenant+container
    target_id = tenant_id+":"+container_id
    pipeline = r.hgetall("pipeline:AUTH_" + target_id)
    if not pipeline:
        # ...else target with only tenant
        target_id = tenant_id
        pipeline = r.hgetall("pipeline:AUTH_" + target_id)

    # for each policy in the pipeline
    lambda_policy_id = None
    for policy_id, json_encoded_policy in pipeline.items():
        policy_dict = json.loads(json_encoded_policy)

        if policy_dict['filter_name'] == settings.JOB_ANALYZER_LAMBDA_PUSHDOWN_FILTER:
            lambda_policy_id = policy_id

    # We assume that a single tenant/container only has one pushdown filter
    if lambda_policy_id:
        return target_id, lambda_policy_id
    else:
        raise AnalyticsJobSubmissionException("There is no lambda pushdown filter configured for this tenant and container.")


def update_lambda_params(target_id, policy_id, lambdas_to_migrate):
    r = get_redis_connection()

    logger.debug("Lamdas to migrate:" + str(lambdas_to_migrate))
    lambdas_as_string = ''
    index = 0
    for x in lambdas_to_migrate:
        lambdas_as_string += str(index) + "-lambda=" + str(x['lambda-type-and-body']) + ","
        index += 1

    policy_redis = r.hget("pipeline:AUTH_" + str(target_id), policy_id)
    json_data = json.loads(policy_redis)
    json_data.update({'params': lambdas_as_string[:-1]})
    r.hset("pipeline:AUTH_" + str(target_id), policy_id, json.dumps(json_data))


def update_filter_params(lambdas_to_migrate, job_execution_data):
    target_id, policy_id = get_current_lambda_pushdown_policy(job_execution_data['tenant_id'], job_execution_data['container_id'])

    update_lambda_params(target_id, policy_id, lambdas_to_migrate)


def init_job_submission(job_execution_data):

    r = get_redis_connection()

    # STEP 1: Execute the JobAnalyzer
    analyzer_file_name = r.hget('analyzer:' + str(job_execution_data['analyzer_id']), 'analyzer_file_name')
    job_analyzer_path = os.path.join(settings.ANALYZERS_DIR, str(analyzer_file_name))
    spark_job_path = os.path.join(settings.JOBS_DIR, str(job_execution_data['job_file_name']))

    spark_job_name = job_execution_data['_simple_name']
    spark_job_migratory_name = job_execution_data['name']

    jsonObject = executeJavaAnalyzer(job_analyzer_path, spark_job_path)

    # STEP 2: Get the lambdas and the code of the Job
    lambdasToMigrate = jsonObject.get("lambdas")
    originalJobCode = jsonObject.get("original-job-code")
    pushdownJobCode = jsonObject.get("pushdown-job-code")

    # STEP 3: Decide whether or not to execute the lambda pushdown
    pushdown = job_execution_data['pushdown']
    jobToCompile = originalJobCode

    # STEP 4: Set the lambdas in the storlet if necessary
    if pushdown:
        # TODO: Maybe we have to handle error codes and do something
        update_filter_params(lambdasToMigrate, job_execution_data)
        jobToCompile = pushdownJobCode
    else:
        update_filter_params([], job_execution_data)

    # STEP 5: Compile pushdown/original job
    executor_location = settings.JOB_ANALYZER_EXECUTOR_LOCATION
    m = re.search('package\s*(\w\.?)*\s*;', jobToCompile)
    jobToCompile = jobToCompile.replace(m.group(0),
                                        'package ' + executor_location.replace('/', '.')[1:-1] + ';')
    jobToCompile = jobToCompile.replace(spark_job_name, spark_job_migratory_name)

    jobFile = open(executor_location + '/' + spark_job_migratory_name + '.java', 'w')
    print >> jobFile, jobToCompile
    jobFile.close()

    logger.info("Starting compilation")
    cmd = settings.JOB_ANALYZER_JAVAC_PATH + ' -cp \"' + settings.JOB_ANALYZER_SPARK_LIBS_LOCATION + '*\" '
    cmd += executor_location + spark_job_migratory_name + '.java'
    logger.info(">> EXECUTING: " + cmd)
    proc = subprocess.call(cmd, shell=True)
    if proc != 0:
        raise AnalyticsJobSubmissionException("javac error compiling " + spark_job_migratory_name)

    # STEP 6: Package the Spark Job class as a JAR and set the manifest
    logger.info("Starting packaging")
    cmd = 'jar -cfe ' + executor_location + spark_job_migratory_name + '.jar ' + \
          executor_location.replace('/', '.')[1:] + spark_job_migratory_name + ' ' + \
          executor_location + spark_job_migratory_name + '.class'
    logger.info(">> EXECUTING: " + cmd)
    proc = subprocess.call(cmd, shell=True)
    if proc != 0:
        raise AnalyticsJobSubmissionException("jar error packaging " + spark_job_migratory_name)

    '''STEP 7: In cluster mode, we need to store the produced jar in HDFS to make it available to workers'''
    if settings.JOB_ANALYZER_CLUSTER_MODE:
        logger.info("Starting to store the JAR in HDFS")
        cmd = settings.JOB_ANALYZER_HDFS_LOCATION + ' -put -f ' + executor_location + spark_job_migratory_name + '.jar ' + \
              ' /' + spark_job_migratory_name + '.jar'
        logger.info(">> EXECUTING: " + cmd)
        proc = subprocess.call(cmd, shell=True)
        if proc != 0:
            raise AnalyticsJobSubmissionException("There was a problem storing the " + spark_job_migratory_name + " JAR in HDFS")

    # STEP 7: Execute the job against Swift
    logger.info("Starting execution")
    if settings.JOB_ANALYZER_CLUSTER_MODE:
        deploy_mode = 'cluster'
        jar_location = 'hdfs://' + settings.JOB_ANALYZER_HDFS_IP_PORT + '/' + spark_job_migratory_name + '.jar'
    else:
        deploy_mode = 'client'
        jar_location = executor_location + spark_job_migratory_name + '.jar'
    cmd = 'bash ' + settings.JOB_ANALYZER_SPARK_FOLDER + 'bin/spark-submit --deploy-mode ' + deploy_mode + \
          ' --master ' + settings.JOB_ANALYZER_SPARK_MASTER_URL + ' ' + \
          '--class ' + executor_location.replace('/', '.')[1:] + spark_job_migratory_name + ' ' + \
          '--driver-class-path ' + settings.JOB_ANALYZER_SPARK_FOLDER + 'jars/stocator-1.0.9.jar ' + \
          '--executor-cores ' + settings.JOB_ANALYZER_AVAILABLE_CPUS + ' --executor-memory ' + settings.JOB_ANALYZER_AVAILABLE_RAM + \
          ' ' + jar_location + ' --jars ' + settings.JOB_ANALYZER_SPARK_FOLDER + 'jars/*.jar'
    logger.info(">> EXECUTING: " + cmd)
    proc = subprocess.call(cmd, shell=True)
    if proc != 0:
        raise AnalyticsJobSubmissionException("There was a problem submitting the job.")

    # Note: to use FlightRecorderTaskMetrics, add the following line to spark submit call:
    # '--conf spark.extraListeners=ch.cern.sparkmeasure.FlightRecorderStageMetrics,ch.cern.sparkmeasure.FlightRecorderTaskMetrics ' +

    # STEP 8: Clean files
    os.remove(executor_location + spark_job_migratory_name + '.java')
    os.remove(executor_location + spark_job_migratory_name + '.class')
    os.remove(executor_location + spark_job_migratory_name + '.jar')
    os.remove(executor_location + spark_job_name + 'Java8Translated.java')

    r.hset('job_execution:' + str(job_execution_data['id']), 'status', 'submitted')
