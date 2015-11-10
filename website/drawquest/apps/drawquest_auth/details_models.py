from apps.client_details.models import ClientDetailsBase


class UserDetails(ClientDetailsBase):
    TO_CLIENT_WHITELIST = [
        'id',
        'username',
        ('avatar_url', True),
    ]

    @classmethod
    def from_id(cls, user_id):
        from drawquest.apps.drawquest_auth.models import User
        return User.details_by_id(user_id, promoter=cls)()


class PrivateUserDetails(UserDetails):
    TO_CLIENT_WHITELIST = UserDetails.TO_CLIENT_WHITELIST + [
        'email',
    ]

