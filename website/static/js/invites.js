$(function () {
    var metric_info = function (channel) {
        return {
            channel: "onboarding_" + channel,
            share_url: '/',
            share: current.homepage_invite_url,
        };
    };

    $('.invites .facebook').click(function () {
        var name = 'invite_facebook';
        var message = "Hey! I just joined Canvas, a community where people create and remix images together. Come join me! " + current.homepage_invite_url;
        FB.ui({
                method: 'apprequests',
                message: message,
                data: current.homepage_invite_url,
            },
            function (resp) {
                canvas.record_metric('share', metric_info(name));
                canvas.record_metric(name, metric_info(name));

                if (resp && resp.to.length) {
                    onboarding.invited += resp.to.length;
                    onboarding.update_quota();
                    canvas.record_metric('invite_facebook_friends', {
                        friends_invited: resp.to.length,
                        user_id: current.user_id,
                    });
                }
            }
        );
    });

    $('.invites .twitter').click(function () {
        var name = 'invite_twitter';
        canvas.record_metric('share', metric_info(name));
        canvas.record_metric(name, metric_info(name));
        var message = "I just joined @canv_as, a community where people create and remix images together. Come join me! " + current.homepage_invite_url;
        window.open('http://twitter.com/intent/tweet?text=' + encodeURIComponent(message), "twitter_share", "width=600, height=400");
    });

    $('.invites .email').click(function () {
        var name = 'invite_email';
        canvas.record_metric('share', metric_info(name));
        canvas.record_metric(name, metric_info(name));
        var url = current.homepage_invite_url;
        var subject = "Come remix with me on Canvas";
        var body = "Hey! I just joined Canvas, a community where people create and remix images together. Come join me! " + current.homepage_invite_url;
        window.location.href = 'mailto:?subject=' + subject + '&body=' + body;
    });
});

