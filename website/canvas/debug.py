import os
import sys
import threading
import time
import traceback

from debug_toolbar.panels import DebugPanel
from django.template.loader import render_to_string

from redis_models import CanvasRedis
from canvas import util

class RedisPanel(DebugPanel):
    name = 'Redis'
    has_content = True

    def __init__(self, *args, **kwargs):
        DebugPanel.__init__(self, *args, **kwargs)
        self._start = len(CanvasRedis.commands)

    def queries(self):
        return CanvasRedis.commands[self._start:]

    def nav_title(self):
        return 'Redis'

    def nav_subtitle(self):
        q = self.queries()
        count = len(q)
        total_time = sum(time for host, port, db, time, stacktrace, command, size in q)
        total_bytes = sum(size for host, port, db, time, stacktrace, command, size in q) / 1024.0
        return '%(count)s commands in %(total_time)0.02fms (%(total_bytes)0.02fkb)' % locals()

    def title(self):
        return 'Redis Commands'

    def url(self):
        return ''

    def content(self):
        context = {
            'redis_commands': self.queries(),
        }
        return render_to_string('widget/debug_redis_panel.django.html', context)

class StackMonitor(object):

    singleton = None
    

    @classmethod
    def ensure(cls):
        if not cls.singleton:
            cls.singleton = StackMonitor()
        
        return cls.singleton

    def __init__(self):
        self.interval = 0.01
        self.pid = os.getpid()        
        self.output = file('/var/canvas/website/run/sample.%s.log' % self.pid, 'a')
        self.output.write('spawned\n')
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()
    
    def run(self):
        self.output.write("StackMonitor running\n")
        while True:
            time.sleep(self.interval)
            self.sample()
            
    def sample(self):
        t = time.time()
        frames = sys._current_frames()
        my_frame = sys._getframe()
        for thread, frame in frames.items():
            if frame == my_frame:
                continue
                                
            if '/gunicorn/' in frame.f_code.co_filename:
                continue
                
            header = "Stack Monitor pid: %s time: %s thread: %s\n" % (self.pid, t, thread)
            self.output.write(header + "".join(traceback.format_stack(frame)))
            
        
        
