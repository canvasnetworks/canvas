from functools import wraps

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext

from apps.public_api.util import (public_api_method, short_id, long_id)
from apps.public_api.models import (PublicAPICommentDetails, PublicAPIGroupDetails, PublicAPIUserDetails)
from canvas import util, knobs, stickers, experiments, fact
from canvas.api_decorators import json_service
from canvas.cache_patterns import CachedCall
from canvas.exceptions import ServiceError
from canvas.metrics import Metrics
from canvas.models import User, Comment, Thread
from canvas.view_helpers import CommentViewData

@public_api_method
def root(request, payload={}):
    """
    Root of the example.com public api

    Available endpoints are:

        /public_api/
        /public_api/users/
        /public_api/posts/
        /public_api/groups/
    """
    pass

@public_api_method
def posts(request, payload={}, short_id=None):
    """
    Posts endpoint of the example.com public api

    Request with an id parameter:

        /public_api/posts/1qkx8

    POST JSON in the following format:

        POST /public_api/posts/
        {"ids":["1qkx8","ma6fz"]}
    """
    Metrics.api_comment.record(request)
    ids = payload.get('ids')

    if short_id and not ids:
        try:
            comment = Comment.details_by_id(long_id(short_id), promoter=PublicAPICommentDetails)
            (comment,) = CachedCall.multicall([comment])
            return comment.to_client()
        except (ObjectDoesNotExist, util.Base36DecodeException):
            raise ServiceError("Post not found")

    elif ids:
        ids = [long_id(x) for x in set(ids)]
        calls = [Comment.details_by_id(id, ignore_not_found=True, promoter=PublicAPICommentDetails) for id in ids]
        comments = CachedCall.multicall(calls, skip_decorator=True)
        return {'posts': [x.to_client() for x in comments if x]}

@public_api_method
def users(request, payload={}, username=None):
    """
    Users endpoint of the example.com public api

    Request with an id parameter:

        /public_api/users/watermelonbot

    POST JSON in the following format:

        POST /public_api/users/
        {"ids":["watermelonbot", "jeff"]}

    User posts will be returned """ + str(knobs.PUBLIC_API_PAGINATION_SIZE) + """ at a time, ordered newest to oldest. You can request posts beyond the initial range by POSTing JSON in the following format:

        POST /public_api/users/
        {"ids":[{"user":"watermelonbot","skip":100},"jeff"}
    """
    Metrics.api_user.record(request)
    if username and not payload:
        try:
            return PublicAPIUserDetails(username).to_client()
        except (ObjectDoesNotExist, Http404):
            raise ServiceError("User does not exist")

    elif payload:
        def inner_user(user_arg):
            try:
                return PublicAPIUserDetails(user_arg).to_client()
            except (ObjectDoesNotExist, Http404):
                return None

        potential_users = [inner_user(x) for x in payload.get('ids')]
        return {'users': [x for x in potential_users if x]}

@public_api_method
def groups(request, payload={}, group_name=None):
    """
    Groups endpoint of the example.com public api

    Request with an id parameter:
        /public_api/groups/funny

    POST JSON in the following format:
        POST /public_api/groups/
        {"ids":["funny","canvas"]}

    Group posts will be returned """ + str(knobs.PUBLIC_API_PAGINATION_SIZE) + """ at a time, ordered newest to oldest. You can request posts beyond the initial range by POSTing JSON in the following format:

        POST /public_api/groups/
        {"ids":[{"group":"funny","skip":100},"canvas"}
    """
    Metrics.api_group.record(request)
    ids = payload.get('ids')

    if group_name and not ids:
        try:
            return PublicAPIGroupDetails(group_name).to_client()
        except (ObjectDoesNotExist, Http404):
            raise ServiceError("Group does not exist")

    elif ids:
        def inner_group(group_arg):
            try:
                return PublicAPIGroupDetails(group_arg).to_client()
            except (ObjectDoesNotExist, Http404):
                return None

        potential_groups = [inner_group(x) for x in payload.get('ids')]
        return {'groups': [x for x in potential_groups if x]}


