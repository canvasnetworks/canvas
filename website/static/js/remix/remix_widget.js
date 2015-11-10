remix.RemixWidget = canvas.BaseWidget.createSubclass();

remix.RemixWidget.prototype.init = function (pw, root, logged_out_posting, is_quest) {
    remix.RemixWidget.__super__.init.call(this, root);

    this.closed = true;

    this.pw = pw;
    this.easel = new remix.Easel(root);
    this.current_panel = null;
    this.loading_count = 0;

    this.logged_out_posting = logged_out_posting || false;
    this.is_quest = is_quest || false;

    this.loading_mask = this.scoped('.loading');
    this.uploading_mask = this.scoped('.uploading');
    this.upload_percentage = this.scoped('.uploading .fill');
    this.tool_picker = this.scoped('.tool_picker');
    this.popout_wrapper = this.scoped('.popout_wrapper');

    this.noop_tool = new remix.Tool(this.easel.renderer);

    this._wire_container();
    this._wire_events();
    this._wire_text();
    this._wire_images();
    this._wire_draw();
    this._wire_layers();
    this._wire_undo_redo();
    this._wire_cancel();
    this._wire_help();
    this._wire_window_blur();

    this.bind_window();

    this.pick_tool(this.noop_tool);

    this.pw.attachRemix(this);
};

remix.RemixWidget.prototype._wire_container = function () {
    $(this.root).animate({
        opacity: 1,
    }, 400);
};

remix.RemixWidget.prototype.bind_window = function () {
    var self = this;
    // Make sure the user can't leave the page without confirmation while remix is open
    window.onbeforeunload = function () {
        if (!self.closed
            && self.easel.renderer
            && self.easel.renderer.history
            && self.easel.renderer.history.past.length) {
            return "Are you sure you want to leave? You will lose all progress on your remix.";
        }
    };

    // We need to make sure the enter key doesn't cause click behavior
    // when trying to confirm entry in a popout input.
    $(this.pw.container).delegate(".popout input[type=text]", "keypress", function(e) {
        if (e.keyCode == 13) {
            // On enter, just close the popout
            $(this).parents('.panel_picker').children('button').trigger('click');
            remix.Popout.hide_all();
            e.preventDefault();
        }
    });
};

remix.RemixWidget.prototype.unbind_window = function () {
    window.onbeforeunload = undefined;
};

remix.RemixWidget.prototype._tool_closed = function (button) {
    remix.Popout.hide_all();
    if ($(button).hasClass('selected')) {
        this._close_panel();
        return true;
    }
    return false;
};

remix.RemixWidget.prototype._wire_window_blur = function() {
    $(window).bind("blur", $.proxy(function(event) {
        remix._shift_down = false;
        remix._alt_down = false;
        remix._meta_down = false;
    }, this));
};

remix.RemixWidget.prototype._wire_events = function () {
    $(this.root).bind('loading', $.proxy(this.loading, this));
    $(this.root).bind('done_loading', $.proxy(this.done_loading, this));

    $(this.root).bind('use_temporary_tool', $.proxy(this.use_temporary_tool, this));
    $(this.root).bind('finish_temporary_tool', $.proxy(this.finish_temporary_tool, this));
};

remix.RemixWidget.prototype._wire_cancel = function () {
    this.scoped('.cancel_remix').click($.proxy(function (event) {
        event.preventDefault();
        if (this.remix_has_changes()) {
            // Make a save button, this way the user has the option to save her changes
            // Note that calling $() with a single tag uses the native document.createElement
            // so it is just as fast.
            save_button = $("<input />").attr("class", "button_cancel")
                                       .attr("value", "Download remix")
                                       .attr("type", "submit");
            save_button.click($.proxy(function () {
                window.open(this.to_data_url(), '_blank');
            }, this));
            new canvas.ConfirmDialog({
                title: "Exit Remix?",
                message: "Are you sure? You have a remix open and will lose ALL the progress.",
                cancel_text: "Keep working",
                ok_text: "Exit remix",
                success: $.proxy(function () {
                    this.close();
                }, this),
                extra_buttons: save_button,
            });
        } else {
            this.close();
        }
    }, this));
};

remix.RemixWidget.prototype._wire_help = function() {
    this.scoped('.help a').click($.proxy(function(event) {
        new canvas.RemixShortcutsDialog();
    }, this));
};

remix.RemixWidget.prototype._toggle_close_button = function () {
    this.scoped('a.cancel_remix').toggle();
};

remix.RemixWidget.prototype._hide_close_button = function () {
    this.scoped('a.cancel_remix').hide();
};

remix.RemixWidget.prototype._show_close_button = function () {
    this.scoped('a.cancel_remix').show();
};

remix.RemixWidget.prototype._wire_draw = function () {
    var self = this;

    var tool_meta = {};
    var draw_button = this.tool_picker.find('.draw');

    var pick_tool_by_name = function (name) {
        var meta = tool_meta[name];

        var provider = meta.panel ? $.proxy(meta.panel.get_params, meta.panel) : null;
        var tool = new meta.ToolClass(self.easel.renderer, provider);
        tool.easel = self.easel;

        self.pick_tool(tool, meta.panel);
    };

    var bind_tool = function (name, ToolClass, PanelClass) {
        var panel = null;
        var panel_el = self.scoped('.panel.' + name);
        if (panel_el.length) {
            panel = new PanelClass(panel_el, self.easel);
        }

        tool_meta[name] = {
            ToolClass: ToolClass,
            panel: panel
        };

        popout.scoped('.' + name).data('name', name);
    };

    this.tool_picker.find('.draw').click(function () {
        if ($(this).hasClass('selected') && self.scoped('.draw_popout.popped').length) {
            remix.Popout.hide_all();
            return;
        }
        pick_tool_by_name($(this).data('name'));
        popout.show_right_of(this);
        self._select_button(this);
    }).bind('mousedown', function () {
        popout.click_away_to_dismiss = false;

        // Fire after the popout's mousedown listener.
        setTimeout(function () {
            popout.click_away_to_dismiss = true;
        }, 0);
    });

    var popout = new remix.Popout(this.scoped('.draw_popout'));

    popout.root.delegate('button.tool', 'click', function () {
        var button = $(this);
        popout.scoped('button').removeClass('selected');
        button.addClass('selected');
        popout.hide();
        draw_button.html('<div class="icon ' + button.text() + '"></div>' + button.text());
        draw_button.data('name', button.data('name'));
        pick_tool_by_name(button.data('name'));
        self._select_button(self.tool_picker.find('.draw'));
    });

    draw_button.data('name', 'brush');
    bind_tool('brush', remix.Airbrush.Tool, remix.panels.BrushPanel);
    bind_tool('eraser', remix.Eraser.Tool, remix.panels.EraserPanel);
    bind_tool('fill', remix.Fill.Tool, remix.panels.FillPanel);
    bind_tool('shape', remix.Shape, remix.panels.ShapePanel);
    bind_tool('clone', remix.Clone.Tool, remix.panels.ClonePanel);
};

remix.RemixWidget.prototype._wire_images = function () {
    var self = this;

    var images_button = this.tool_picker.find('button.images');
    var panel = new remix.panels.ImagePanel(this.scoped('.panel.images'), this.easel);

    var add_image = function (img, content) {
        var tool = new remix.StampLibrary(self.easel.renderer, $.proxy(panel.get_params, panel));
        tool.easel = self.easel;
        tool.mode = 'new';
        tool.set_image(img, content);
        tool.place();
        self.pick_tool(tool);
        popout.hide();
        images_button.removeClass('selected');
        self._switch_panel(panel);
        self._show_close_button();
    };

    var popout = new remix.ImagesPopout(
        this.scoped('.images_popout'),
        {
            click_away_to_dismiss: false,
            add_image: add_image,
        }
    );

    images_button.click(function () {
        self._toggle_close_button();
        if (self._tool_closed(this)) {
            return;
        }
        self._switch_panel(null);
        self._select_button(this);
        popout.show_right_of(this);
        popout.show_default();
    });
};

remix.RemixWidget.prototype._wire_layers = function () {
    var self = this;
    var layer_popout = new remix.LayersPopout(this.scoped('.layers_popout'), {
        easel: this.easel,
        click_away_to_dismiss: false,
    });

    this.tool_picker.find('button.layers').click(function () {
        if (self._tool_closed(this)) {
            return;
        }
        var button = $(this);
        self.pick_tool(self.noop_tool);
        layer_popout.show_right_of(button);
        self._select_button(button);
    });
};

remix.RemixWidget.prototype._wire_text = function () {
    var self = this;

    var popout = new remix.Popout(this.scoped('.text_prompt_popout'), {click_away_to_dismiss: false});
    var panel = new remix.panels.TextPanel(this.scoped('.panel.text'), this.easel);
    var parameter_provider = $.proxy(panel.get_params, panel);
    var text_input = popout.scoped('input[type=text]');

    var create_text = function () {
        popout.hide();
        panel.text = text_input.val();
        text_input.val("");
        var text_tool = new remix.Text(self.easel.renderer, parameter_provider);
        text_tool.easel = self.easel;
        self.pick_tool(text_tool, panel);
        self._select_button($());
        text_input.unbind('keypress');
    };

    this.tool_picker.find('button.text').click(function (e) {
        if (self._tool_closed(this)) {
            return;
        }
        var button = $(this);
        self.pick_tool(self.noop_tool);
        popout.show_right_of(button);
        text_input.focus();
        text_input.bind('keypress', function (event) {
            if (event.which == 13 /* ENTER */) {
                create_text();
                event.preventDefault();
            }
        });
        self._select_button(button);
    });

    popout.scoped('button').click(create_text);
};

remix.RemixWidget.prototype._wire_undo_redo = function () {
    var self = this;
    var undo = this.scoped('.undo_redo .undo');
    var redo = this.scoped('.undo_redo .redo');

    this.root.bind('history_update', function (event, has_past, has_future) {
        undo.toggleDisabled(!has_past);
        redo.toggleDisabled(!has_future);
    });
    
    undo.click(function () {
        self.easel.renderer.finish_current_tool();
        self.easel.renderer.history.undo();
        var tool_name = self.easel.current_tool.tool_name;
        if(tool_name == "text" || tool_name == "stamps") {
            self.pick_tool(self.noop_tool, null, false);
        }
    });
    redo.click(function () { self.easel.renderer.history.redo(); });
};

remix.RemixWidget.prototype._close_panel = function () {
    remix.Popout.hide_all();
    this.tool_picker.find('button').removeClass('selected');
    if (this.current_panel) {
        this.current_panel.leave();
        this.current_panel = null;
    }
};

remix.RemixWidget.prototype._switch_panel = function (panel) {
    this._close_panel();

    this.current_panel = panel;

    if (this.current_panel) {
        this.current_panel.enter();
    }
};

remix.RemixWidget.prototype._select_button = function (button) {
    this.tool_picker.find('button').removeClass('selected');
    $(button).addClass('selected');
};

remix.RemixWidget.prototype.scroll_to = function () {
    var remixer_top = $(this.root).offset().top;
    var nav_height = $('#header .top_bar').outerHeight();
    var image_chooser_height = $('.image_chooser').outerHeight();
    if (!$('.image_chooser').is(':visible')) {
        image_chooser_height = 0;
    }
    var top = remixer_top - nav_height - image_chooser_height;
    $('html, body').animate({
        scrollTop: top,
    }, 500, 'swing');
};

remix.RemixWidget.prototype.pick_tool = function (tool, panel, temporary) {
    if (!temporary) {
        this._switch_panel(panel);
        this._show_close_button();
    }
    this.easel.cursor(tool.cursor);
    this.easel.use_tool(tool, temporary);
};

remix.RemixWidget.prototype.finish_current_tool = function (done) {
    this.easel.renderer.finish_current_tool(done);
};

remix.RemixWidget.prototype.remix_has_changes = function () {
    return Boolean(this.easel.renderer.history.past.length);
};

remix.RemixWidget.prototype.close = function () {
    this.closed = true;
    this._unbind_keyboard();

    $(this.pw.container).trigger('closing');

    $(this.root).animate({
        opacity: 0,
    }, 75, $.proxy(function () {
        $(this.root).hide();
    }, this));
};

remix.RemixWidget.prototype.install_actions = function () {
    var self = this;
    action.remix = function (content_id, source) {
        if (!current.logged_in && !self.logged_out_posting) {
            canvas.encourage_signup('remix');
            return false;
        }
        var metric_info = {
            source: source || 'thread_footer_link',
        };
        canvas.record_metric('attempted_remix', metric_info);

        var load_remix = function () {
            self.load_content(content_id);
            self.scroll_to();
            $(self.pw.container).trigger('opening');
            self._bind_keyboard();
        };

        if (!self.closed &&
            self.easel.renderer &&
            self.easel.renderer.history &&
            self.easel.renderer.history.past.length) {
            new canvas.ConfirmDialog({
                title: "Start a new Remix?",
                message: "Are you sure? You already have a remix open and will lose ALL the progress of that one.",
                cancel_text: "Cancel",
                ok_text: "Start New Remix",
                success: function () {
                    load_remix();
                }
            });
        } else {
            load_remix();
        }
    };
};

remix.RemixWidget.prototype.loading = function () {
    var self = this;

    this.loading_count++;
    this.loading_mask.show().css('opacity', 0);
    this._loading_timout = setTimeout(function () { self.loading_mask.css('opacity', ''); }, 500);
};

remix.RemixWidget.prototype.done_loading = function () {
    this.loading_count--;
    if (this.loading_count < 0) {
        this.loading_count = 0;
    }
    if (this.loading_count == 0) {
        clearTimeout(this._loading_timeout);
        this.loading_mask.hide();
    }
};

remix.RemixWidget.prototype.uploading = function() {
    this.uploading_mask.show();  
};

remix.RemixWidget.prototype.done_uploading = function() {
    this.uploading_mask.hide();
};

remix.RemixWidget.prototype.use_temporary_tool = function (event, data) {
    var tool = null;
    if (data.args.length) {
        tool = new data.tool(this.easel.renderer, data.args);
    } else {
        tool = new data.tool(this.easel.renderer);
    }

    this.previous_tool = this.easel.renderer.current_tool;
    this.pick_tool(tool, null, true);
};

remix.RemixWidget.prototype.finish_temporary_tool = function (event, data) {
    if (this.previous_tool) {
        this.pick_tool(this.previous_tool, null, true);
        this.previous_tool = null;
    }
};

remix.RemixWidget.prototype.load_content = function (content_id) {
    this.root.show();
    this.closed = false;
    this.root.css('opacity', '');
    this.easel.load_content(canvas.getContent(content_id));

    if (this._activity_timer) {
        this._activity_timer.stop();
    }

    this._activity_timer = new ActivityTimer(this.root, 30000);

    this.pick_tool(this.noop_tool);
};

remix.RemixWidget.prototype.to_data_url = function (content_id) {
    this.finish_current_tool();
    return this.easel.renderer.composite[0].toDataURL('image/png');
};

remix.RemixWidget.prototype._bind_keyboard = function () {
    var pick_shape = $.proxy(function (shape) {
        return $.proxy(function () {
            this.scoped('.shape.tool').click();
            this.scoped('.shape_picker .' + shape).click();
        }, this);
    }, this);

    var pick_text = $.proxy(function () {
        this.scoped('.tool_picker button.text').click();
    }, this);

    var pick_stamp = $.proxy(function () {
        this.scoped('.tool_picker button.images').click();
    }, this);

    var pick_eye_dropper = $.proxy(function () {
        this.scoped('.panel:visible button.eye_dropper').click();
    }, this);

    var pick_tool = $.proxy(function (tool) {
        return $.proxy(function () {
            this.scoped('.tool.' + tool).click();
            if (tool === 'fill' || tool === 'knockout') {
                this.scoped('.tool.fill').click();
                this.scoped('.fill_eraser').attr('checked', tool === 'knockout');
            }
        }, this);
    }, this);

    var swap_layers = $.proxy(function () {
        this.easel.swap(true);
    }, this);

    var merge_layers = $.proxy(function () {
        this.easel.merge(true);
    }, this);

    var tools = {
        A: [pick_tool('brush')],
        B: [pick_tool('brush'), 'Brush'],
        I: [pick_eye_dropper, 'Eye-dropper'],
        R: [pick_shape('rectangle'), 'Rectangle'],
        O: [pick_shape('ellipse'), 'Ellipse'],
        L: [pick_shape('line'), 'Line'],
        F: [pick_tool('fill'), 'Fill'],
        G: [pick_tool('fill')],
        P: [pick_tool('fill')],
        X: [pick_tool('knockout'), 'Knockout'],
        W: [pick_tool('knockout')],
        E: [pick_tool('eraser'), 'Eraser'],
        T: [pick_text, 'Text'],
        C: [pick_tool('clone'), 'Clone'],
        Alt: [null, 'Clone resample'],
        S: [pick_stamp, 'Images/stamps'],
        N: [swap_layers, 'Swap layers'],
        M: [merge_layers, 'Merge layers'],
    };

    canvas.RemixShortcutsDialog.shortcuts = [];
    $.each(tools, function (shortcut, details) {
        if (details.length >= 2) {
            canvas.RemixShortcutsDialog.shortcuts.push([shortcut, details[1]]);
        }
    });
    $.each([
        ['Hold Shift', 'Draw straight'],
        ['Hold ' + canvas.get_meta_key_name(), 'Precision cursor'],
        [canvas.get_meta_key_name() + ' + Z', 'Undo'],
        [canvas.get_meta_key_name() + ' + Y', 'Redo'],
        ['?', "This guide"]
    ], function (_, shortcut) {
        canvas.RemixShortcutsDialog.shortcuts.push(shortcut);
    });

    // Prevent backspace from causing the browser to navigate back
    $(window).bind('keydown.remix_widget_global', $.proxy(function (event) {
        // Tool modifiers are globally recognized, because they should only affect when you mouse over
        if (event.keyCode == 18 && this.easel.renderer.current_tool) {
            this._alt_down = true;
            this.easel.renderer.current_tool.alt_down();
        }
        if (event.keyCode == 16 && this.easel.renderer.current_tool) {
            remix._shift_down = true;
            this.easel.renderer.current_tool.shift_down();
        }

        // Don't steal input from input tags or contenteditable tags.
        var modifier_key = (canvas.get_meta_key_name() === 'cmd') ? (event.metaKey && !event.ctrlKey) : event.ctrlKey;
        var tag_name = event.target.tagName;
        var is_editable = event.target.getAttribute("contenteditable");

        if (modifier_key) {
            this._meta_down = true;
        }

        if (tag_name === 'INPUT' || tag_name === 'TEXTAREA' || is_editable) {
            return;
        }

        var key = String.fromCharCode(event.keyCode);

        if (event.keyCode === 191 && event.shiftKey) {
            new canvas.RemixShortcutsDialog();
            event.preventDefault();
            return;
        }

        if (!modifier_key) {
            var tool = tools[key];

            if (tool && typeof tool[0] == 'function') {
                tool[0]();
                event.preventDefault();
            }
        }

        // Undo
        if (event.keyCode == 8  /* backspace */ || (modifier_key && key === 'Z')) {
            this.easel.renderer.history.undo();
            var tool_name = this.easel.current_tool.tool_name;
            if(tool_name == "text" || tool_name == "stamps") {
                this.pick_tool(this.noop_tool, null, false);
            }
            event.preventDefault();
        }

        // Redo
        if (modifier_key && key === 'Y') {
            this.easel.renderer.history.redo();
            event.preventDefault();
            var a = 5;
        }

        // Crosshair cursor when meta key is down
        if (this._meta_down) {
            this.easel.cursor("url(/static/img/remix-ui/precision-crosshair.png) 7 7, auto");
        }
    }, this));

    $(window).bind('keyup.remix_widget_global', $.proxy(function (event) {
        var modifier_key = (canvas.get_meta_key_name() === 'cmd') ? (event.metaKey && !event.ctrlKey) : event.ctrlKey;
        if (!modifier_key) {
            this._meta_down = false;
        }
        if (event.keyCode == 18 && this.easel.renderer.current_tool) {
            this._alt_down = false;
            this.easel.renderer.current_tool.alt_up();
        }
        if (event.keyCode == 16 && this.easel.renderer.current_tool) {
            remix._shift_down = false;
            this.easel.renderer.current_tool.shift_up();
        }
        if (!this._meta_down) {
            this.easel.cursor(this.easel.renderer.current_tool.cursor);
        }
    }, this));
};

remix.RemixWidget.prototype._unbind_keyboard = function () {
    $(window).unbind('keydown.remix_widget_global');
    $(window).unbind('keyup.remix_widget_global');
};

remix.RemixWidget.prototype.upload = function (on_done) {
    var self = this;

    this.easel.renderer.finish_current_tool();

    var upload_hooks = $({})
        .bind('uploadstart', function () {
            self.uploading();
        })
        .bind('uploadprogress', function (e, progress) {
            self.upload_percentage.text(progress.percentage);
            self.upload_percentage.css("width", progress.percentage + "%");
        })
        .bind('uploadfail', function (e, reason) {
            self.done_uploading();

            var message = "Upload failed :(", save_button = null;
            if (canvas.is_chrome()) {
                window.URL = window.webkitURL || window.URL;
                window.BlobBuilder = window.BlobBuilder || window.WebKitBlobBuilder ||
                                    window.MozBlobBuilder;

                // http://stackoverflow.com/questions/4998908/convert-data-uri-to-file-then-append-to-formdata
                function data_uri_to_blob (data_uri) {
                    // convert base64 to raw binary data held in a string
                    // doesn't handle URLEncoded DataURIs
                    var byte_string = atob(data_uri.split(',')[1]);

                    // separate out the mime component
                    var mime = data_uri.split(',')[0].split(':')[1].split(';')[0]

                    // write the bytes of the string to an ArrayBuffer
                    var ab = new ArrayBuffer(byte_string.length);
                    var ia = new Uint8Array(ab);
                    for (var i = 0; i < byte_string.length; i++) {
                        ia[i] = byte_string.charCodeAt(i);
                    }

                    // write the ArrayBuffer to a blob, and you're done
                    var bb = new BlobBuilder();
                    bb.append(ab);
                    return bb.getBlob(mime);
                }

                // http://html5-demos.appspot.com/static/a.download.html
                var blob = data_uri_to_blob(self.to_data_url());

                save_button = $("<a></a>").attr({
                    class: "button_cancel button",
                    download: 'canvas_remix.png',
                    href: window.URL.createObjectURL(blob),
                    target: '_blank',
                }).text("Download remix");
            } else {
                message += '<p>To download your remix, <a href="' + self.to_data_url() + '" target="_blank">right-click here</a> and choose Save As.</p>';
            }

            new canvas.ConfirmDialog({
                title: "Error",
                message: message,
                cancel_text: "Cancel",
                ok_text: "Try again",
                success: function () {
                    self.upload(on_done);
                },
                extra_buttons: save_button,
            });
        })
        .bind('uploadend', function (event, content) {
            self.done_loading();
            on_done(content);
        });

    return canvas.upload_canvas_chunked(this.easel.renderer.composite, upload_hooks, this.easel.renderer.metadata, this.is_quest);
};

remix.RemixWidget.prototype.get_metadata = function () {
    return {
        'active_time': this._activity_timer.get_time(),
    }
};

