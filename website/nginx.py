#!/usr/bin/env python
import sys; sys.path.append('/var/canvas/common')

from optparse import OptionParser
import grp
import os
import platform
import pwd
import random
import signal
import string
import time

from configuration import Config, PRODUCTION

randstr = lambda length: ''.join(random.choice(string.lowercase + string.digits) for n in range(length))

options = None

WEBSITE_PATH = '/var/canvas/website'
TEMPLATE_PATH = WEBSITE_PATH

def gunicorn_settings_file():
    if options.project == 'canvas':
        return 'settings_gunicorn.py'
    return 'settings_{0}_gunicorn.py'.format(options.project)

def project_path(force_project=None):
    project = force_project or options.project

    if project == 'canvas':
        return WEBSITE_PATH
    return os.path.join(WEBSITE_PATH, project)

def run_path(force_project=None):
    project = force_project or options.project

    run_path = os.path.join(project_path(force_project=project), 'run')
    if not os.path.isdir(run_path):
        os.makedirs(run_path)
    return run_path

def django_settings_file():
    if options.project == 'canvas':
        return 'settings.py'
    return 'settings_{}.py'.format(options.project)

def generate_nginx_conf(name, context=None):
    from jinja2 import FileSystemLoader, Environment

    env = Environment(loader=FileSystemLoader(TEMPLATE_PATH))
    template = env.get_template('%s.conf.template' % name)

    context = context or {}
    return template.render(production=PRODUCTION, **context)

def write_nginx_conf(name, context=None):
    rendered_conf = generate_nginx_conf(name, context=context)

    # New hotness
    file(run_path() + '/%s.rendered.conf' % name, 'w').write(rendered_conf)
    # Old and ugly!
    file(project_path() + '/%s.conf' % name, 'w').write(rendered_conf)

def read_pid(name, force_project=None):
    project = force_project or options.project

    # Hard-coded relative path for realtime/server.py simplicity, except for drawquest.
    # test_nginx.py also expects this unless server.py is updated to not hard-code it either.
    if name == 'twistd':
        # Awful temporary special-case hack, since I don't want to code
        # twisted stuff to also know where the per-project run path is
        # (which doesn't matter as much since we don't run twisted locally for drawquest).
        filename = './run/{}.pid'.format(name)
    elif project == 'drawquest':
        filename = os.path.join(run_path(force_project=project), '{}.pid'.format(name))
    else:
        filename = './run/%s.pid' % name

    try:
        pid = int(file(filename).read())
        os.kill(pid, signal.SIG_DFL)
    except (ValueError, IOError, OSError) as e:
        try:
            os.remove(filename)
        except OSError:
            pass

        return None

    return pid

def read_port(name):
    # see read_pid for reasons why *.port's path is hard-coded.
    filename = './run/%s.port' % name
    return int(file(filename).read())

def gunicorn():
    pid = read_pid('gunicorn')
    if pid:
        print "Gunicorn", pid, "sending SIGHUP"
        os.kill(pid, signal.SIGHUP)
    else:
        print "Spawning new Gunicorn"
        # On Linux hardcode the gunicorn path so we don't have PATH issues for example with Puppet. 
        # Don't hardcode the path in sandboxes so we can virtualenv. 
        if platform.system() == 'Darwin':
            xvfb = ''
        else:
            xvfb = '''xvfb-run --server-args="-screen 0 1024x768x24" '''
        gunicorn_django = '/usr/local/bin/gunicorn_django' if platform.system() != "Darwin" else 'gunicorn_django'
        cmd = xvfb + gunicorn_django + " -c {} {}".format(gunicorn_settings_file(), django_settings_file())
        return os.system(cmd)

def wait_for_file(filename):
    for x in range(100):
        # Wait for the file to have actually been written to, avoiding a race condition.
        if os.path.exists(filename) and len(file(filename).read()):
            break
        time.sleep(0.05)
    else:
        raise Exception("Timed out waiting for %s" % filename)

def twisted():
    old_pid = read_pid('twistd')
    if old_pid:
        print "Twistd running", old_pid
        os.rename('./run/twistd.pid', './run/twistd.pid.old')
        os.kill(old_pid, signal.SIGUSR1)

    # see read_pid for reasons why twisted.port's path is hard-coded.
    if os.path.exists('./run/twisted.port'):
        os.rename('./run/twisted.port', './run/twisted.port.old')

    print "Spawning new twistd"
    pidfile = os.path.abspath("./run/twistd.%s.pid" % randstr(10))
    logfile = os.path.abspath('./run/twistd.log')
    settings_name = django_settings_file().rstrip('.py')
    returncode = os.system("PYTHONPATH=. DJANGO_SETTINGS_MODULE=%(settings_name)s twistd -y production.tac --pidfile=\"%(pidfile)s\" --logfile=\"%(logfile)s\"" % locals())
    if returncode:
        return returncode

    wait_for_file(pidfile)

    os.symlink(pidfile, os.path.abspath('./run/twistd.pid'))

    wait_for_file('./run/twisted.port')

def get_nginx_context():
    ctx = {
        'run_path': run_path(),
        'twisted_host': None,
        'project': options.project,
    }
    if (options.project == 'canvas'
        or (options.project == 'drawquest' and PRODUCTION)):
        ctx['twisted_host'] = "127.0.0.1:%s" % read_port('twisted')
    return ctx

def nginx(name, context=None):
    write_nginx_conf(name, context=context)
    pid = read_pid(name)
    if pid:
        print "Nginx running", pid, "sending SIGHUP"
        os.kill(pid, signal.SIGHUP)
    else:
        print "Spawning new " + name
        return os.system("nginx -c \"%s\"" % os.path.abspath(run_path() + '/%s.rendered.conf' % name))

def remove_stale_pyc():
    return os.system('find /var/canvas/ -name "*.pyc" | xargs rm -f')

def reconfig():
    results = {}
    results['remove_stale_pyc'] = remove_stale_pyc()

    if not options.factlog:
        results['gunicorn'] = gunicorn()
        if (options.project == 'canvas'
            or (options.project == 'drawquest' and PRODUCTION)):
            results['twisted'] = twisted()
        results['nginx'] = nginx('nginx', context=get_nginx_context())

    if options.factlog or not PRODUCTION:
        results['nginx-factlog'] = nginx('nginx-factlog')

    if any(results.values()):
        print "Some services failed to run: %s" % results
        sys.exit(1)

    print "All services are happy."

def main(argv):
    reconfig()

def get_options_and_args():
    """ options get set in global namespace. """
    parser = OptionParser()
    parser.add_option('--project', dest='project', default='canvas')
    parser.add_option('--factlog', action='store_true', default=False, dest='factlog')

    global options
    options, args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = get_options_and_args()
    main(args)

