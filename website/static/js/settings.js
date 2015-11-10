settings = {};

settings.wire_facebook = function () {
    window.fbReady.done(function () {
        var connect_section = $('.fb_signup_wrapper');

        $('button', connect_section).bind('mousedown', function (event) {
            FB.login(function(response) {
                settings.check_facebook_status();
            }, {scope: 'email,publish_actions'});
        });

        FB.Event.subscribe('auth.login', function (response) {
        });

        settings.check_facebook_status();

    });
};

settings.check_facebook_status = function () {
    var connection_name = $('.connection_name');
    FB.getLoginStatus(function(response) {
        if (response.authResponse) {
            FB.api('/me', function(me){
                if (me.first_name) {
                    connection_name.text('Connected as ' + me.name);
                    canvas.api.set_facebook(me.id);
                }
            });
            $('.connected').show();
            $('.disconnected').hide();
        } else {
            $('.connected').hide();
            $('.disconnected').show();
        }
    });
};
