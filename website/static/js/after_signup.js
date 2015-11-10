var after_signup = {};

after_signup._record = function (key, val) {
    // Session cookie.
    $.cookie('after_signup_' + key, JSON.stringify(val), {path: '/'});
};

after_signup.post_comment = function (post) {
    after_signup._record('post_comment', post);
};

after_signup.redirect_to = function (url) {
    after_signup._record('redirect_to', url);
};

