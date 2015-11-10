from drawquest.apps.drawquest_auth.models import User

def followers(user):
    """ The users who are following `user`. """
    return User.objects.in_bulk_list(user.redis.followers.smembers())

def following(user):
    """ The users that `user` is following. """
    return User.objects.in_bulk_list(user.redis.following.smembers())

def counts(user):
    return {
        'followers': user.redis.followers.scard(),
        'following': user.redis.following.scard(),
    }

