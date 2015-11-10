from django.core.management.base import BaseCommand

from canvas.js_api import generate_api_javascript, get_api_js_filename

class Command(BaseCommand):
    args = ''
    help = "Auto generates canvas_api.js. Run this everytime you add a new call to api.py"

    def handle(self, *args, **options):
        api_js_code = generate_api_javascript()
        output_filename = get_api_js_filename()
        with open(output_filename, "w") as js_file:
            js_file.write(api_js_code)

        print "Generated %s successfully." % output_filename


