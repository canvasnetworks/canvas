from django.dispatch import Signal

user_email_changed = Signal(providing_args=['user', 'new_email', 'old_email'])

