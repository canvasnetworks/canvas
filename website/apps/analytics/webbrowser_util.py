import platform
import webbrowser

def open_if_able(filename):
    if platform.system() == 'Darwin':
        # Don't automagically open when running this script in the cluster
        webbrowser.open("file://" + filename)

