#!/usr/bin/env python
import os, signal, time, string, sys
sys.path.append('/var/canvas/common')


def read_pid(name):
    '''
    Returns a tuple with the PID and its filename.
    '''
    filename = './run/%s.pid' % name
    try:
        pid = int(file(filename).read())
        os.kill(pid, signal.SIG_DFL)
    except (ValueError, IOError, OSError) as e:
        try:
            os.remove(filename)
        except OSError:
            pass
            
        pid = None
        
    return (pid, filename,)

def gunicorn():
    pid, pid_filename = read_pid('sentry.gunicorn')
    if pid:
        print "Gunicorn", pid, "sending SIGHUP"
        os.kill(pid, signal.SIGHUP)
    else:
        print "Spawning new Gunicorn"
        # Hardcode the gunicorn path so we don't have PATH issues for example with Puppet. The README ensures this should be true for everyone.
        return os.system("/usr/local/bin/gunicorn_django -c settings_sentry_gunicorn.py --pid={0} settings_sentry.py".format(pid_filename))
        
def reconfig():
    result = gunicorn()
    if result:
        print "gunicorn failed to run: %s" % result
        sys.exit(1)
    print "All services are happy."

def main():
    reconfig()
    
if __name__ == "__main__":
    main()

