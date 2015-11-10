from django.core.exceptions import PermissionDenied

from apps.ip_blocking.models import is_ip_blocked
from canvas.view_guards import view_guard


@view_guard
def require_unblocked_ip(request):
    if is_ip_blocked(request):
        raise PermissionDenied()

