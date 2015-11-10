(function( $ ){
    // A simple tooltip plugin

    var default_settings = {
        container       :   $("body"),
        tooltip_class   :   "tooltip",
        extra_classes   :   "", 
        content         :   "",
        attribute       :   "title",            
        append          :   true,
        track_mouse     :   false,
        h_center        :   true,
        left            :   0,
        right           :   0,
        top             :   5,
        bottom          :   0, 
        delay_on        :   300,
        delay_off       :   0, 
        fade_in         :   200,
        fade_out        :   100,
        disabled        :   false,
        hover_on_timer  :   "",
        hover_off_timer :   "",
        delegate        :   null,
        escape_html     :   true,
    };

    var methods = {
        // Initiate instance
        init: function(params) {
            var settings = $.extend({}, default_settings, params);
            settings.tooltip_element = $('<div class="' + settings.tooltip_class + '"></div>');
            $(this).data("tooltip", {settings: settings});
            var $that = $(this);

            var hover_on = function(e) {
                clearTimeout(settings.hover_off_timer);
                if(settings.delay_on) {
                    settings.hover_on_timer = setTimeout(function() {
                        $that.tooltip('render', [settings, e]);
                    }, settings.delay_on);
                } else {
                    $(this).tooltip('render', [settings, e]);
                }               
            }

            var hover_off = function(e) {
                clearTimeout(settings.hover_on_timer);
                if (settings.delay_off) {
                    settings.hover_off_timer = setTimeout(function() {
                        $that.tooltip('remove', [settings]);
                    }, settings.delay_off);
                } else {    
                    $(this).tooltip('remove', [settings]);
                }
            }

            if (!settings.disabled) {
                if (!settings.delegate) {
                    $that.bind("mouseenter.tooltip", hover_on).bind("mouseleave.tooltip", hover_off);
                } else {
                    settings.delegate.delegate($that.selector, "mouseenter", hover_on).delegate($that.selector, "mouseleave", hover_off);
                }
            }
            return this;
        },

        // Create and append the tooltip
        render: function(args) {
            var settings = args[0],
            e = args[1];
            settings.tooltip_element.html("");
            if (settings.title) {
                if (!settings.escape_html) {
                    var title = $('<p><strong>' + settings.title + '</strong></p><hr>');
                } else {
                    var title = $('<p><strong>' + canvas.escape_html(settings.title) + '</strong></p><hr>');
                }
                settings.tooltip_element.append(title);
            }
            // Support reading tooltips from html attributes. Default is title.
            var title = settings.content;
            if ((settings.content == "") && settings.attribute){
                var element = $(e.target);
                if (!element.hasClass("tooltipped")) {
                    element = element.parents(".tooltipped");
                }
                if (element.attr(settings.attribute)){
                    // hide the title attribute to suppress the native tooltip
                    element
                        .data("tooltip", element.attr(settings.attribute))
                        .removeAttr(settings.attribute);
                } 
                title = element.data("tooltip");
            }
            if (!settings.escape_html) {
                var content = $('<p>' + title + '</p>');
            } else {
                var content = $('<p>' + canvas.escape_html(title) + '</p>');
            }

            settings.tooltip_element.append(content);
            if (settings.append) {
                settings.tooltip_element.appendTo(settings.container);
            } else {
                settings.tooltip_element.prependTo(settings.container);
            }

            if (settings.extra_classes) {
                settings.tooltip_element.addClass(settings.extra_classes);
            }

            if (settings.track) {
                // SET THIS UP IF WE NEED IT
            } else {
                if (settings.h_center) {
                    settings.tooltip_element.css("left", Math.min($(document).width() - 5 - settings.tooltip_element.outerWidth(true), Math.max($(e.target).offset().left + $(e.target).outerWidth(true)/2 - settings.tooltip_element.outerWidth(true)/2, 5)));
                } else if (settings.left || !settings.right) {
                    settings.tooltip_element.css("left", Math.min($(document).width() - 5 - settings.tooltip_element.outerWidth(true), Math.max($(e.target).offset().left + this.outerWidth(true) + settings.left, 5)));
                } else if (settings.right) {
                    settings.tooltip_element.css("right", Math.min($(document).width() - 5 - settings.tooltip_element.outerWidth(true), Math.max($(e.target).offset().left - settings.right, 5)));
                }

                if (settings.top || !settings.bottom) {
                    settings.tooltip_element.css("top", $(e.target).offset().top + $(e.target).outerHeight(true) + settings.top);
                } else if (settings.bottom) {
                    settings.tooltip_element.css("bottom", $(e.target).offset().top - settings.bottom);
                }
            }

            if (settings.fade_in) {
                settings.tooltip_element.css("opacity", 0).animate({opacity:1}, settings.fade_in);
            }
            return this;
        },

        // Remove the tooltip
        remove: function(args) {
            settings = args[0];
            if (settings.fade_out) {
                settings.tooltip_element.animate({opacity:0}, settings.fade_out, function() {
                    $(this).remove();
                });
            } else {
                settings.tooltip_element.remove();
            }
            return this;
        },

        // New text
        newContent: function(args) {
            var settings = this.data('tooltip').settings;
            new_content = args[0];
            settings.content = new_content;
            $(this).tooltip('remove', [this.data('tooltip').settings]);
        },

        // Unbind tooltip
        clear: function() {
            if (this.data("tooltip")) {
                var settings = this.data('tooltip').settings;
                clearTimeout(settings.hover_on_timer);
                $("."+ settings.tooltip_class).remove();
                this.unbind(".tooltip");
            }
            return this;
        },

        // Reinit with old settings
        reset: function() {
            if (this.data("tooltip")) {
                this.tooltip($(this).data("tooltip").settings);
            }
            return this;
        }
    };

    $.fn.tooltip = function(method) {
        if (methods[method]) {
            return methods[ method ].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || ! method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' +  method + ' does not exist on jQuery.tooltip');
        }   
    };
})( jQuery );
