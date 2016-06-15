from django.conf import settings
import subprocess


def add_new_sds_project(tenant_name):
    
    admin_user = settings.MANAGMENT_ADMIN_USERNAME
    admin_password = settings.MANAGMENT_ADMIN_PASSWORD
    admin_account = settings.MANAGMENT_ACCOUNT
    bin_dir = settings.STORLET_BIN_DIR
    docker_image = settings.STORLET_DOCKER_IMAGE
    tar_file = settings.STORLET_TAR_FILE

    python add_new_tenant.py tenant_name admin_user admin_password
    python deploy_image.py tenant_name tar_file docker_image

    p = subprocess.Popen()