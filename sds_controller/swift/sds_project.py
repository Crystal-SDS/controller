from django.conf import settings
import subprocess

def add_new_sds_project(tenant_name):
    admin_user = settings.MANAGEMENT_ADMIN_USERNAME
    admin_password = settings.MANAGEMENT_ADMIN_PASSWORD
    bin_dir = settings.STORLET_BIN_DIR
    docker_image = settings.STORLET_DOCKER_IMAGE
    tar_file = settings.STORLET_TAR_FILE
    
    print "Creating new SDS project"
    print 'sudo python '+bin_dir+'/add_new_tenant.py '+tenant_name+' '+admin_user+' '+admin_password
    new_project = subprocess.Popen(['sudo','python', bin_dir+'/add_new_tenant.py', tenant_name, admin_user, admin_password])
    new_project.communicate()
    
    print "Deploying docker images"
    print 'sudo python '+bin_dir+'/deploy_image.py '+tenant_name+' '+tar_file+' '+docker_image
    deploy_image = subprocess.Popen(['sudo','python', bin_dir+'/deploy_image.py', tenant_name, tar_file, docker_image])
    deploy_image.communicate()
