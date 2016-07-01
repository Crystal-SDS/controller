from django.conf import settings
import subprocess


def add_new_sds_project(tenant_name):
    admin_user = settings.MANAGEMENT_ADMIN_USERNAME
    admin_password = settings.MANAGEMENT_ADMIN_PASSWORD
    admin_account = settings.MANAGEMENT_ACCOUNT
    bin_dir = settings.STORLET_BIN_DIR
    docker_image = settings.STORLET_DOCKER_IMAGE
    tar_file = settings.STORLET_TAR_FILE

    new_project = subprocess.Popen([bin_dir+'/add_new_tenant.py', tenant_name, admin_user, admin_password], shell=True, stdout=subprocess.PIPE)
    print "Creating new SDS project"
    new_project.communicate()
    
    deploy_image = subprocess.Popen([bin_dir+'/deploy_image.py', tenant_name, tar_file, docker_image], shell=True, stdout=subprocess.PIPE)
    print "Deploying docker images"
    deploy_image.communicate()
