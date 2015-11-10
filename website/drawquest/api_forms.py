from canvas.exceptions import ValidationError

def validate(form):
    """
    Raises a ValidationError if invalid. Puts form-level errors into a "non_field_errors" key.
    """
    errors = {}

    if form.is_valid():
        return

    errors['non_field_errors'] = form.non_field_errors()
    errors.update(form.errors)

    try:
        del errors['__all__']
    except KeyError:
        pass

    raise ValidationError(errors)

