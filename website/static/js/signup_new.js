window.signup_new = {};

signup_new.wire = function(parent) {
    var signup_form = new signup_new.SignupForm(parent);
    signup_form.wire();
    return signup_form;
};

signup_new.SignupForm = function(parent) {
    this.nodes = {
        inputs              : $('.input_wrapper input', parent),
        username_input      : $('.username input', parent),
        email_input         : $('.email input', parent),
        password_input      : $('.password input', parent),
        button              : $('.signup_button', parent),
        facebook            : $('.facebook', parent),
        fb_button           : $('.facebook_login_button', parent),
        almost_there        : $('.almost_there', parent),
        email_header_msg    : $('.email_signup_wrapper p.header_message', parent),
        signup_wrapper      : $('.email_signup_wrapper', parent),
        fb_id               : $('.fb_id', parent),
        divider             : $('p.divider', parent),
        form                : $('form', parent),
        signed_request      : $('.signed_request', parent),
        not_person          : $('.not_person', parent),
    };
};

signup_new.SignupForm.prototype.wire = function() {
    var self = this;

    canvas.bind_label_to_input(self.nodes.inputs);
    self.bind_validation(self.nodes.inputs);
    self.nodes.button.click(self.submit);
    window.fbReady.done(function() {
        self.facebook_wire();
    });

    self.nodes.fb_button.bind('mousedown', function (event) {
        FB.login(function(response) {
            self.check_facebook_status();
        }, {scope: 'email,publish_actions'});
    });
};

signup_new.SignupForm.prototype.facebook_wire = function() {
    var self = this;
    FB.Event.subscribe('auth.login', function (response) {
        self.check_facebook_status();
    });
    self.check_facebook_status();
};

signup_new.SignupForm.prototype.check_facebook_status = function() {
    var self = this;
    FB.getLoginStatus(function(response) {
        if (response.authResponse) {
            var signed_request = response.authResponse.signedRequest;
            self.nodes.facebook.hide();
            self.nodes.email_header_msg.text("Just enter a username and password");
            FB.api('/me', function(me){
                if (me.first_name) {
                    self.nodes.almost_there.text("Almost there, " + me.first_name + "!");
                    self.nodes.almost_there.show();
                }
                if (me.email) {
                    self.nodes.email_input.val(me.email);
                    self.nodes.email_input.parent().children("label").addClass("hidden");
                    self.validate_input(self.nodes.email_input);
                }
                canvas.api.facebook_exists(me.id).done(function (response) {
                    if (response.exists) {
                        self.nodes.facebook.show();
                        self.nodes.almost_there.text("Welcome back, " + me.first_name + "!");
                        self.nodes.not_person.text("Not " + me.first_name + "?");
                        self.nodes.not_person.click( function() {
                            FB.logout(function () {
                                self.reset();

                            });
                        });
                        self.nodes.fb_button.text("Login with Facebook");
                        self.nodes.signup_wrapper.hide();
                        self.nodes.divider.hide();

                        self.nodes.fb_button.unbind('click');
                        self.nodes.fb_button.bind('click', function() {
                            self.nodes.fb_id.val(me.id)
                            self.nodes.signed_request.val(signed_request);
                            self.nodes.form.attr('action', 'https://' + document.domain + '/login');
                            self.nodes.form.submit();
                        });
                    }
                });
                self.nodes.fb_id.val(me.id);
            });
            self.nodes.username_input.focus();
        }
    });
};

signup_new.SignupForm.prototype.reset = function () {
    var self = this;
    // put the button text back
    self.nodes.fb_button.text("Sign up with Facebook");

    // put the email stuff back
    self.nodes.email_input.val('');
    self.nodes.email_input.parent().children("label").removeClass("hidden");
    self.validate_input(self.nodes.email_input);

    // hide the not link
    self.nodes.not_person.text('');

    // show and hide the right sections
    self.nodes.facebook.show();
    self.nodes.divider.show();
    self.nodes.signup_wrapper.show();
    self.nodes.almost_there.hide();
};

signup_new.SignupForm.prototype.enable_button = function() {
    // Check that all inputs are good before we enable
    var all_valid = true;
    for (var i = 0; i < this.nodes.inputs.length; i++) {
        var input = $(this.nodes.inputs[i]);
        if (input.parent().hasClass("invalid")) {
            all_valid = false;
        }
    }
    if (all_valid) {
        this.nodes.button.removeAttr("disabled");
    } else {
        this.disable_button();
    }
};

signup_new.SignupForm.prototype.disable_button = function() {
    this.nodes.button.attr("disabled", true);
};

signup_new.SignupForm.prototype.show_hint = function(input, message) {
    var hint = input.next(".input_hint");
    hint.css({
        opacity     : 0,
        display     : "block",
    }).text(message).animate({
        opacity : 1,
    }, 200);
};

signup_new.SignupForm.prototype.hide_hint = function(input) {
    var hint = input.next(".input_hint");
    if (!hint.length) { return; }
    hint.stop().animate({
        opacity     : 0,
    }, 200, function() {
        $(this).css({
            opacity     : 1,
            display     : "none",
        }).text("");
    });
};

signup_new.SignupForm.prototype.validate_username = function(input, value, callback) {
    var self = this;
    var api_response = function(response) {
        if (!response.success) {
            self.show_hint(input, response.reason);
        }
        callback(response.success);
    }
    canvas.api.user_exists(value).done(api_response).fail(api_response);
};

signup_new.SignupForm.prototype.validate_password = function(input, value, callback) {
    if (value.length < 5) {
        this.show_hint(input, "Your password must be at least 5 characters.");
        result = false;
    } else {
        result = true;
    }
    callback(result);
};

signup_new.SignupForm.prototype.validate_email = function(input, value, callback) {
    if (value.match(/.+@.+\..+/gi)) {
        result = true;
    } else {
        this.show_hint(input, "Please enter a valid email address.");
        result = false;
    }
    callback(result);
};

signup_new.SignupForm.prototype.validate_input = function(input) {
    var self = this;
    var value = input.val();
    var input_wrapper = input.parent();
    var validation_callback = function(validation_result) {
        if (validation_result === true) {
            input_wrapper.addClass("valid").removeClass("invalid");
            self.enable_button();
        } else if (validation_result === false) {
            input_wrapper.removeClass("valid").addClass("invalid");
            self.disable_button();
        } else if (validation_result === undefined) {
            // If the value is empty
            input_wrapper.removeClass("valid").removeClass("invalid");
            self.enable_button();
        }
    };
    if (!value.length) {
        validation_callback(undefined);
    } else if (input_wrapper.hasClass("username")) {
        validation_result = this.validate_username(input, value, validation_callback);
    } else if (input_wrapper.hasClass("email")) {
        validation_result = this.validate_email(input, value, validation_callback);
    } else if (input_wrapper.hasClass("password")) {
        validation_result = this.validate_password(input, value, validation_callback);
    }
};

signup_new.SignupForm.prototype.bind_validation = function(inputs) {
    var keydown_timeout;
    var self = this;
    inputs.bind("keydown.signup", function(e) {
        if (!canvas.keycode_is_valid(e.keyCode)) { return; }
        var this_input = $(this);
        self.hide_hint(this_input);
        clearTimeout(keydown_timeout);
        keydown_timeout = setTimeout(function() {
            self.validate_input(this_input);
        }, 500);
    }).bind("keyup.signup", function(e) {
        if (!canvas.keycode_is_valid(e.keyCode)) { return; }
        self.enable_button();
    }).bind("blur", function() {
        clearTimeout(keydown_timeout);
        self.validate_input($(this));
    });
};

signup_new.SignupForm.prototype.submit = function() {
    // Go ahead and validate email and password since we can do those fast
    this.validate_input(this.nodes.email_input);
    this.validate_input(this.nodes.password_input);
    var all_valid = true;
    for (var i = 0; i < this.nodes.inputs.length; i++) {
        var input = $(this.nodes.inputs[i]);
        if (!input.parent().hasClass("valid")) {
            all_valid = false;
        }
        if (!input.val().length) {
            this.show_hint(input, "You forgot to fill this out");
        }
    }
    if (!all_valid) {
        this.disable_button();
    }
};
