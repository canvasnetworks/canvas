from canvas.management.commands.canvas_app import Command as CanvasAppCommand

class Command(CanvasAppCommand):
    def handle_label(self, app_name, directory=None, **options):
        if directory is None:
            import website.drawquest.apps
            directory = website.drawquest.apps.__path__[0]
        import drawquest
        template_path = drawquest.__path__[0]
        return super(Command, self).handle_label(app_name, directory=directory, template_path=template_path,
                                                 **options)

