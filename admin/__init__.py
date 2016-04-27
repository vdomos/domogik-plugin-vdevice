# -*- coding: utf-8 -*-

### common imports
from flask import Blueprint, abort
from domogik.common.utils import get_packages_directory
from domogik.admin.application import render_template
from domogik.admin.views.clients import get_client_detail
from jinja2 import TemplateNotFound

### package specific imports
import subprocess



### package specific functions
def get_errorlog(cmd, log):
    print("Command = %s" % cmd)
    errorlog = subprocess.Popen([cmd, log], stdout=subprocess.PIPE)
    output = errorlog.communicate()[0]
    if isinstance(output, str):
        output = unicode(output, 'utf-8')
    return output



### common tasks
package = "plugin_vdevice"
template_dir = "{0}/{1}/admin/templates".format(get_packages_directory(), package)
static_dir = "{0}/{1}/admin/static".format(get_packages_directory(), package)
geterrorlogcmd = "{0}/{1}/admin/geterrorlog.sh".format(get_packages_directory(), package)
logfile = "/var/log/domogik/{0}.log".format(package)

plugin_vdevice_adm = Blueprint(package, __name__,
                        template_folder = template_dir,
                        static_folder = static_dir)


@plugin_vdevice_adm.route('/<client_id>')
def index(client_id):
    detail = get_client_detail(client_id)
    try:
        return render_template('plugin_vdevice.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            errorlog = get_errorlog(geterrorlogcmd, logfile))
    except TemplateNotFound:
        abort(404)

