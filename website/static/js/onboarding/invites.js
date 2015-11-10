$(function () {
    if (!$('.onboarding').length) {
        return;
    }

    onboarding.invited = 0;

    onboarding.quota_fulfillment = function () {
        return onboarding.invited;
    };

    $('.invites').find('.twitter, .email').click(function (event) {
        event.preventDefault();
        onboarding.allow_advancement();
    });
});

