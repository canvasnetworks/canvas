from mongrel2.config import *

web_app_proxy = Proxy(addr='127.0.0.1', port=80) 
 
static_dir = Dir(base='static/', 
                    index_file='index.html', 
                    default_ctype='text/plain') 
 
django_wsgi = Handler(send_spec='tcp://127.0.0.1:9997', 
                      send_ident='34f9ceee-cd52-4b7f-b197-88bf2f0ec378', 
                      recv_spec='tcp://127.0.0.1:9996', recv_ident='') 

realtime = Handler(send_spec='tcp://127.0.0.1:9999', 
                   send_ident='54c6755b-9628-40a4-9a2d-cc82a816345e', 
                   recv_spec='tcp://127.0.0.1:9998', recv_ident='')  

# the r'' string syntax means to not interpret any \ chars, for regexes 
mongrel2 = Host(name="test.example.com", routes={
    r'/static/': static_dir,
    r'/realtime/': realtime,
    r'/': django_wsgi
})

main = Server( 
    uuid="2f62bd5-9e59-49cd-993c-3b6013c28f05", 
    access_log="/logs/access.log", 
    error_log="/logs/error.log", 
    pid_file="run/mongrel2.pid", 
    default_host="test.example.com", 
    chroot="./",
    name="main", 
    port=80,
    hosts=[mongrel2],
) 

settings = {"zeromq.threads": 1} 
 
commit([main], settings=settings)
