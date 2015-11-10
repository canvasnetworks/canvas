from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.utils.datastructures import SortedDict

from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--format', default='json', dest='format',
            help='Specifies the output serialization format for fixtures.'),
        make_option('-e', '--exclude', dest='exclude',action='append', default=[],
            help='App to exclude (use multiple --exclude to exclude multiple apps).'),
        make_option('--stop-on-errors', action='store_true', dest='stop_on_errors',
            help='Stop on encountering the first serialization error.'),
    )
    help = 'Identify all objects that are causing serialization errors.'
    args = '[appname ...]'

    def handle(self, *app_labels, **options):
        import sys, traceback
        from django.db.models import get_app, get_apps, get_models, get_model

        format = options.get('format','json')
        exclude = options.get('exclude',[])
        show_traceback = options.get('traceback', False)
        stop_on_errors = options.get('stop_on_errors', False)

        excluded_apps = [get_app(app_label) for app_label in exclude]

        if len(app_labels) == 0:
            app_list = SortedDict([(app, None) for app in get_apps() if app not in excluded_apps])
        else:
            app_list = SortedDict()
            for label in app_labels:
                try:
                    app_label, model_label = label.split('.')
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)

                    model = get_model(app_label, model_label)
                    if model is None:
                        raise CommandError("Unknown model: %s.%s" % (app_label, model_label))

                    if app in app_list.keys():
                        if app_list[app] and model not in app_list[app]:
                            app_list[app].append(model)
                    else:
                        app_list[app] = [model]
                except ValueError:
                    # This is just an app - no model qualifier
                    app_label = label
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
                    app_list[app] = None

        # Check that the serialization format exists; this is a shortcut to
        # avoid collating all the objects and _then_ failing.
        if format not in serializers.get_public_serializer_formats():
            raise CommandError("Unknown serialization format: %s" % format)

        try:
            serializers.get_serializer(format)
        except KeyError:
            raise CommandError("Unknown serialization format: %s" % format)

        objects = []
        for app, model_list in app_list.items():
            if model_list is None:
                model_list = get_models(app)

            for model in model_list:
                if not model._meta.proxy:
                    sys.stderr.write('Searching %s\n' % model)
                    try:
                        # Try serializing the whole lot first, before going one by one
                        serializers.serialize(format, model._default_manager.all())
                    except:
                        for instance in model._default_manager.all():
                            try:
                                serializers.serialize(format, model._default_manager.filter(pk=instance.pk))
                            except Exception, e:
                                sys.stderr.write('\nERROR IN %s instance: %s\n' % (model, `instance`))
                                sys.stdout.write('%s\n' % instance.__dict__)
                                if stop_on_errors:
                                    raise
                                else:
                                    sys.stderr.write(traceback.format_exc())
