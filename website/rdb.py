import sys
import pdb
import socket

class Rdb(pdb.Pdb):
    def __init__(self, port=4444):
        self.old_stdout = sys.stdout
        self.old_stdin = sys.stdin

        print socket.gethostbyname(socket.gethostname())
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.sock.bind((socket.gethostbyname(socket.gethostname()), port)) # Binds to the IP
        self.sock.bind(('0.0.0.0', port,))
        self.sock.listen(1)

        (clientsocket, address) = self.sock.accept()

        handle = clientsocket.makefile('rw')
        pdb.Pdb.__init__(self, completekey='tab', stdin=handle, stdout=handle)
        sys.stdout = sys.stdin = handle

    def do_continue(self, arg):
        sys.stdout = self.old_stdout
        sys.stdin = self.old_stdin
        self.sock.close()
        self.set_continue()
        return 1

    do_c = do_cont = do_continue

def set_trace(port=4444):
    print 'debugger waiting on :%d' % port
    db = Rdb(port=port)
    return db.set_trace()

