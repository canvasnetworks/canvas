var onboarding = {};

onboarding.advance = function () {
    window.location = $('button.onboarding_next').data('onboarding_next');
};

onboarding.allow_advancement = function () {
    $('.onboarding .advancement').find('.button_overlay, .skip_step').hide();
};

onboarding.update_quota = function () {
    var remaining = onboarding.quota - onboarding.quota_fulfillment();

    if (remaining <= 0) {
        onboarding.allow_advancement();
    } else {
        $('.quota').text(remaining);
        $('.quota_plurality').text(remaining > 1 ? 's' : '');
    }
};

$(function () {
    if (!$('.onboarding').length) {
        return;
    }

    $('button.onboarding_next').click(function (event) {
        event.preventDefault();
        onboarding.advance();
    });

    if ($('.quota').length && onboarding.quota_fulfillment) {
        onboarding.quota = parseInt($('.quota').text(), 10);
        onboarding.update_quota();
    }
});

