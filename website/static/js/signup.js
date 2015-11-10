signup = {};
signup.vals = {};

signup.scoped = function (selector) {
    return $(selector, signup.container);
};

signup.keycode_is_valid = function (keycode) {
    var unwanted_codes = [9, 13, 16, 17, 37, 38, 39, 40, 91];
    for (var i = 0; i < unwanted_codes.length; i++) {
        if (keycode == unwanted_codes[i]) {
            return false;
        }
    }
    return true;
};

signup.throw_error = function (error_message, input) {
    if (input && input.length) {
        var input_name = input.attr("class").split(" ").shift();
        if (input_name == "password" || input_name == "password_verify") {
            signup.scoped("input[type=password]").addClass("invalid");
        } else {
            input.addClass("invalid");
        }
        signup.scoped("input[type=submit]").attr("disabled", true);
        input.parent().siblings("." + input_name + "_alert")
            .children("span").text(error_message)
            .end().slideDown(100);
        signup.vals[input_name] = input.val();
    } else {
        signup.scoped(".feedback_message").html(error_message).slideDown(100);
    }
};

signup.validate_username = function (fun, validate_empty, suppress_error_hide) {
    var input = signup.scoped("input.username");
    if (input.val()) {
        canvas.apiPOST(
            '/user/exists',
            {
                username: input.val(),
            }, 
            function (response) {
                if (!response.success) {
                    signup.throw_error(response.reason, input);
                } else {
                    input.addClass("valid").removeClass("invalid");
                    // Double check that the user isn't receiving an old error message fuck yeah
                    input.parent().siblings("." + input.attr("class").split(" ").shift() + "_alert")
                        .children("span").text("")
                        .end().stop().slideUp(10);
                    signup.scoped("input[type=submit]").attr("disabled", false);
                    if (!suppress_error_hide) {signup.scoped(".feedback_message").text("").hide();}
                }
                if (fun) { fun(); }
            }
        );
    } else if (validate_empty) {
        signup.throw_error("Please enter your desired username.", input);
    }
};

signup.validate_passwords = function () {
    var inputs = signup.scoped("input.[type=password]");
    // Adding logic for single password field for experiment
    if (inputs.length == 1) {
        if (!inputs.val()) return false;
        if (inputs[0].value.length < 5) {
            signup.throw_error("Your password must be at least 5 characters.", $(inputs[0]));
            return false;
        } else {
            inputs.addClass("valid").removeClass("invalid");
            return true;
        }
    } else {
        if (inputs[0].value != inputs[1].value && !(!inputs[0].value || !inputs[1].value)) {
            signup.throw_error("These passwords do not match.", $(inputs[1]));
            return false;
        } else if (inputs[0].value.length < 5 && !(!inputs[0].value || !inputs[1].value)) {
            signup.throw_error("Your password must be at least 5 characters.", $(inputs[1]));
            return false;
        } else if ((inputs[0].value.length > 4 && inputs[1].value.length > 4) && $(inputs[0]).val() == $(inputs[1]).val()) {
            inputs.addClass("valid").removeClass("invalid");
            return true;
        } else {
            return false;
        }
    }
};

signup.validate_email = function () {
    var input = signup.scoped("input.email");
    var email = input.val();
    if (email) {
        if (email.match(/.+@.+\..+/gi)) {
            input.addClass("valid").removeClass("invalid");
            return true;
        } else {
            signup.throw_error("Please enter a valid email address.", input);
            return false;
        }
    }
};

signup.wire = function () {
    // Input binds
    signup.scoped("input").bind("keyup", function (e) {
        if (!$(this).val()) {
            $(this).parent().children("label").removeClass("hidden");
        }
        if (signup.keycode_is_valid(e.keyCode)) {
            $(this).removeClass("valid");
            input_name = $(this).attr("class").split(" ").shift();
            if ($(this).val() != signup.vals[input_name]) {
                if (input_name == "password" || input_name == "password_verify") {
                    signup.scoped("input[type=password]").removeClass("invalid");
                } else {
                    $(this).removeClass("invalid");
                }

                $(this).parent().siblings("." + input_name + "_alert").slideUp(100, function () {
                    $(this).children("span").text("");
                });
            }

            if (input_name == "username") {
                that = $(this);
                clearTimeout(signup.input_timer);
                signup.input_timer = setTimeout(function () {
                    if (input_name == "username") {
                        signup.validate_username();
                    }
                }, 500);
            }
            signup.scoped(".feedback_message").text("").hide();
        }
    })
    .bind("keydown", function (e) {
        if (signup.keycode_is_valid(e.keyCode)) {
            signup.scoped("input[type=submit]").attr("disabled", false);
            $(this).parent().children("label").addClass("hidden");
        }
    })
    .bind("focus", function () { $(this).parent().children("label").addClass("active"); })
    .bind("blur", function () { $(this).parent().children("label").removeClass("active"); });

    // Bind email if it's there
    if (signup.scoped("input.email")) {
        signup.scoped("input.email").bind("blur", function () { signup.validate_email(); });
    }
    signup.scoped("input.username").bind("blur", function () { signup.validate_username(); });
    signup.scoped("input[type=password]").bind("blur", function () { signup.validate_passwords(); });
    signup.scoped("input[type=submit]").bind("click", function (e) {
        that = this;
        e.preventDefault();
        $(that).attr("disabled", true);
        signup.scoped(".feedback_message").text("").hide();
        if (
            signup.validate_passwords() && signup.scoped("input.username").is(".valid")
            && signup.validate_email() && signup.scoped("input.email").is(".valid")
        ) {
            that.form.submit();
        } else {
            signup.throw_error("Please check that all inputs are properly filled out.");
            $(that).attr("disabled", false);
        }
    });
    signup.scoped('input.username').focus();
};

