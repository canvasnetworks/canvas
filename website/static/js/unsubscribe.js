var unsubscribe = {};

unsubscribe.toggle_option = function(checkbox) {
    li = checkbox.parents("li");
    if (checkbox.is(":checked")) {
        li.addClass("active");
    } else {
        li.removeClass("active");
    }
    if (li.attr("id") === "unsubscribe_all") {
        if (checkbox.is(":checked")) {
            unsubscribe.unsubscribe_all(li[0]);
        } else {
            unsubscribe.resubscribe_all(li[0]);
        }
    }
};

unsubscribe.unsubscribe_all = function(that) {
    $("#page ul.unsubscribe li").each(function() {
        if (this !== that) {
            $(this).removeClass("active");
            $(this).find("input").attr("disabled", true).removeAttr("checked");
        }
    });
};

unsubscribe.resubscribe_all = function(that) {
    $("#page ul.unsubscribe li").each(function() {
        if (this !== that) {
            $(this).addClass("active");
            $(this).find("input").removeAttr("disabled").attr("checked", true);
        }
    });
};

unsubscribe.show_options = function() {
    $("#settings_wrapper").slideDown(200);
    $("#unsubscribe_feedback").hide();
};

unsubscribe.wire = function(unsubscribedData) {
    $("#page ul.unsubscribe li input").bind("click", function() {
        unsubscribe.toggle_option($(this));
    });
    for (key in unsubscribedData){
        var n = "input[name='"+key+"']";
        var flag = unsubscribedData[key];
        if (key == "ALL"){
            flag = !flag;
        }
        if (flag){
            $(n).parents("li").removeClass("active");
        } else {
            $(n).parents("li").addClass("active");
        }
    }
};

