from django.conf import settings
from swiftclient import client
import subprocess


def add_new_sds_project(tenant_name):
    admin_user = settings.MANAGEMENT_ADMIN_USERNAME
    admin_password = settings.MANAGEMENT_ADMIN_PASSWORD
    bin_dir = settings.STORLET_BIN_DIR
    docker_image = settings.STORLET_DOCKER_IMAGE
    tar_file = settings.STORLET_TAR_FILE
    
    print "Creating new SDS project"
    print 'sudo python '+bin_dir+'/add_new_tenant.py '+tenant_name+' '+admin_user+' '+admin_password
    new_project = subprocess.Popen(['sudo', 'python', bin_dir+'/add_new_tenant.py', tenant_name, admin_user, admin_password])
    new_project.communicate()
    
    print "Deploying docker images"
    print 'sudo python '+bin_dir+'/deploy_image.py '+tenant_name+' '+tar_file+' '+docker_image
    deploy_image = subprocess.Popen(['sudo', 'python', bin_dir+'/deploy_image.py', tenant_name, tar_file, docker_image])
    deploy_image.communicate()

    print "Setting container permissions for admin user"
    headers = {'X-Container-Read': '*:' + admin_user, 'X-Container-Write': '*:' + admin_user}
    os_options = {'tenant_name': tenant_name}
    url, token = client.get_auth(settings.KEYSTONE_ADMIN_URL, admin_user, admin_password, os_options=os_options, auth_version="2.0")
    client.post_container(url, token, "storlet", headers)
    client.post_container(url, token, "dependency", headers)
