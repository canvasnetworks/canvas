remix.ImagesPopout = remix.Popout.createSubclass();

remix.ImagesPopout.prototype.init = function (root, params) {
    remix.ImagesPopout.__super__.init.apply(this, arguments);
    this._add_image = params.add_image;
    this._uploaded_content = [];

    this._section_template = this.scoped('.section_template > section');
    this._image_upload = this.scoped('.image_chooser');
    this._upload_error = this.scoped('.upload_error');
    this._image_results = this.scoped('.image_results');
    this._nav_header = this.scoped('header nav');
    this._search = this.scoped('.search input');

    this._wire();
    this._pagination_size = 10;

    this._last_search = null;
};

remix.ImagesPopout.prototype._wire = function () {
    var self = this;

    this.scoped('a').bind('click', function (event) {
        event.preventDefault();
    });

    var upload_foreign_content = function (thumbnail, content) {
        var loading_overlay = new remix.ImagesPopoutLoadingOverlay($(thumbnail).parent());
        var handler = $({})
            .bind('uploadfail', function () {
                loading_overlay.show_message('Image failed, please try another.');
            })
            .bind('uploadend', function (e, local_content) {
                loading_overlay.remove();
                use_content(local_content);
            });
        canvas.upload_url(content.original.url, handler);
    };

    var use_content = function (content) {
        canvas.preload_image(content.original.url, function (image) {
            self._add_image(image, content);
        });
    };

    this.root.delegate('.thumbnail', 'click', function () {
        var content = $(this).data('content');
        if (content.foreign) {
            upload_foreign_content(this, content);
        } else {
            use_content(content);
        }
    });

    this.root.delegate('.thumbnail', 'mousedown', function (event) {
        event.preventDefault();
    });

    this._search.bind('keydown', function (event) {
        if (event.which == 13) {
            event.preventDefault();
            self.search($(this).val());
        }
    });
    this.scoped('.search_icon').bind("click", function () {
        self.search($(this).parent().children("input").val());
    });

    this.scoped('.popular').bind('click', function () {
        self._last_search = null;
        self.show_default();
    });

    this.scoped('.new').bind('click', function () {
        self._last_search = null;
        self.show_new();
    });

    this.scoped('.upload_link').bind('click', function () {
        self._last_search = null;
        self.show_image_chooser();
    });

    canvas.bind_label_to_input(this._search);

    var image_chooser = new canvas.ImageChooser(this.scoped('.image_chooser'));

    var upload_handler = {};

    var overlay;

    $(upload_handler)
        .bind('uploadstart', function () {
            overlay = new remix.ImagesPopoutLoadingOverlay(self.root);
            self._upload_error.text("");
        })
        .bind('uploadfail', function () {
            self._upload_error.text("Upload failed, please try again.");
            overlay.remove();
        })
        .bind('uploadend', function (e, content, response, upload_type) {
            self._uploaded_content.push(content);
            self.show_default();
            overlay.remove();
        });

    image_chooser.url_input_button.click(function (event) {
        var url = image_chooser.url_input_field.val()
        if (url == "http://" || url == this.uploaded_url) {
            return;
        }
        canvas.upload_url(url, upload_handler);
        event.preventDefault();
    });

    canvas.uploadify(image_chooser.scoped('.pw_upload'), upload_handler);
};

remix.ImagesPopout.prototype.toggle_results = function (show_results, save_search) {
    this._image_upload.toggle(!show_results);
    this._image_results.toggle(!!show_results);

    if (show_results) {
        this._image_results.empty();
    }

    if (!save_search) {
        this._search.val("");
    }

    this._upload_error.text("");

    this._nav_header.children().removeClass('selected');
};

remix.ImagesPopout.prototype.search = function (query) {
    this._last_search = query;
    this.toggle_results(true, true);
    this.create_section("Canvas Image Library", canvas.images.get_stamps(query), 2);
    this.create_section("Web Search", canvas.images.get_google_images(query), 2);
};

remix.ImagesPopout.prototype.show_default = function () {
    if (this._last_search) {
        return;
    }
    this.toggle_results(true);
    var image_library_height = 4;
    if (this._uploaded_content.length) {
        var your_images_height = Math.min(2, Math.ceil(this._uploaded_content.length / 5));
        this.create_section("Your Images", new canvas.images.ImageList(this._uploaded_content), your_images_height);
        image_library_height -= your_images_height;
    }
    this.create_section("Canvas Image Library", canvas.images.get_staff_picks(), image_library_height);
    this._nav_header.find('.popular').addClass('selected');
};

remix.ImagesPopout.prototype.show_new = function () {
    this.toggle_results(true);
    this.create_section("Canvas Image Library", canvas.images.get_stamps(""), 4);
    this._nav_header.find('.new').addClass('selected');
};

remix.ImagesPopout.prototype.show_image_chooser = function () {
    this.toggle_results(false);
};

remix.ImagesPopout.prototype._show = function () {
    remix.ImagesPopout.__super__._show.apply(this, arguments);
    this._search.focus();
};

remix.ImagesPopout.prototype.create_section = function (name, source, height) {
    var section = this._section_template.clone();
    this._image_results.append(section);
    return new remix.ImagesPopoutSection(section, name, source, height);
};

remix.ImagesPopoutSection = canvas.BaseWidget.createSubclass();
remix.ImagesPopoutSection.image_width = 5;

remix.ImagesPopoutSection.prototype.init = function (root, name, source, height) {
    remix.ImagesPopoutSection.__super__.init.apply(this, arguments);

    this.name = name;
    this.source = new canvas.images.PagedSource(source, remix.ImagesPopoutSection.image_width * height);
    this.header = this.scoped('h1');
    this.pagination = this.scoped('.pagination');
    this.next = this.pagination.find('.next');
    this.prev = this.pagination.find('.prev');
    this.results = this.scoped('ul.results');

    this.current_page = {
        previous: false,
        next: false,
        images: [],
    };

    this.wire();
};

remix.ImagesPopoutSection.prototype.wire = function () {
    var self = this;

    this.next.bind('click', function (event) {
        if (self.current_page.next) {
            var overlay = new remix.ImagesPopoutLoadingOverlay(self.root);
            self.source.next().done(function (page) {
                overlay.remove();
                self.update_results(page);
            });
        }
    });

    this.prev.bind('click', function () {
        if (self.current_page.previous) {
            self.source.previous().done($.proxy(self.update_results, self));
        }
    });

    this.header.text(this.name);

    var overlay = new remix.ImagesPopoutLoadingOverlay(self.root);
    this.source.start().done($.proxy(function (page) {
        overlay.remove();
        this.update_results(page);
    }, this));
};

remix.ImagesPopoutSection.prototype.update_results = function (page) {
    var self = this;
    this.results.empty();

    $.each(page.images, function (i, item) {
        var thumb = item.content.thumbnail;
        var target_size = { width: 100, height: 100 };

        var fit_size = util.fitInside(target_size.width, target_size.height, thumb)

        var padding = {
            width: (target_size.width - fit_size.width) / 2,
            height: (target_size.height - fit_size.height) / 2,
        };

        var css = {
            width: fit_size.width,
            height: fit_size.height,
            marginTop: padding.height,
            marginBottom: padding.height,
            marginLeft: padding.width,
            marginRight: padding.width,
        }

        var img = $("<img>")
            .addClass('thumbnail')
            .data('content', item.content)
            .attr('src', item.content.thumbnail.url)
            .css(css);
        var li = $("<li></li>");
        li.append(img);

        self.results.append(li);
    });

    this.pagination.toggle(page.previous || page.next);
    this.prev.toggleClass('active', page.previous);
    this.next.toggleClass('active', page.next);
    this.current_page = page;
};

remix.ImagesPopoutLoadingOverlay = canvas.BaseWidget.createSubclass();

remix.ImagesPopoutLoadingOverlay.prototype.init = function (target) {
    remix.ImagesPopoutLoadingOverlay.__super__.init.call(this, $("<div>").addClass('loading'));
    $(target).append(this.root);
    this.show();
};

remix.ImagesPopoutLoadingOverlay.prototype.remove = function () {
    this.root.remove();
};

remix.ImagesPopoutLoadingOverlay.prototype.show_message = function (text) {
    var text = $('<div>').addClass('feedback_text').text(text);
    this.root.removeClass('loading').addClass('feedback_overlay');
    this.root.append(text);
};

