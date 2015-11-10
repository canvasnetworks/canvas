export PYTHONPATH=$PYTHONPATH:.
export DJANGO_SETTINGS_MODULE=settings
epydoc --html -o ../docs canvas realtime
open ../docs/index.html
