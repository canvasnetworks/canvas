import os
from django.core.management.base import NoArgsCommand
from optparse import make_option

class Command(NoArgsCommand):
    help = "Runs the bpython interactive interpreter if it's installed."
    requires_model_validation = False

    def handle_noargs(self, **options):
        from django.db.models.loading import get_models
        loaded_models = get_models()
        locals_ = {}
        for model in loaded_models:
            locals_[model.__name__] = model
        del loaded_models, model, options, get_models
        locals_.update(**locals())
        locals_.pop('locals_')
        locals_.pop('self')
        import bpython
        bpython.embed(locals_)

