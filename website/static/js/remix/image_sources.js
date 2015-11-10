canvas.images = {};

canvas.images.InfiniteSource = function (start, more, template) {
    this.template = template; // old remix, TOKILL
    if (start) {
        this.start = start;
    }
    if (more) {
        this.more = more;
    }
};

canvas.images.InfiniteSource.prototype.more = canvas.images.InfiniteSource.prototype.start = function () {
    return $.when();
};

canvas.images.ImageList = Object.createSubclass();

canvas.images.ImageList.prototype.init = function (images) {
    this.images = images;
};

canvas.images.ImageList.prototype.start = function () {
    return $.when($.map(this.images, function (content) { return {content: content}; }));
};

canvas.images.ImageList.prototype.more = function () {
    return $.when([]);
};

canvas.images.get_stamps = function (query) {
    function get_page (n) {
        var d = $.Deferred();
        canvas.apiPOST('/stamps/search', {"query": query, "start": n*32})
            .done(function (response) {
                var items = $.map(response['comments'], function (comment_data) {
                    var comment = new canvas.Comment(comment_data);
                    return { comment: comment, content: comment.reply_content };
                });
                d.resolveWith(null, [items]);
            });
        return d.promise();
    }
    
    var page = 0;
    function more () {
        return get_page(page++);
    }
    
    return new canvas.images.InfiniteSource(more, more, "stamp");
};

canvas.images.get_staff_picks = function () {
    function get_page (n) {
        var d = $.Deferred();
        canvas.api.staff_pick_stamps(n)
            .done(function (response) {
                var items = $.map(response['comments'], function (comment_data) {
                    var comment = new canvas.Comment(comment_data);
                    return { comment: comment, content: comment.reply_content };
                });
                d.resolveWith(null, [items]);
            });
        return d.promise();
    }

    var page = 0;
    function more () {
        return get_page(page++);
    }

    return new canvas.images.InfiniteSource(more, more)
};

// Pulls image data from Google Images.
//
// http://code.google.com/apis/ajaxsearch/documentation/reference.html#_intro_fonje
//
// This will have to do shenanigans to get more than 64 results (8 pages).
// Ideas: Make requests in parallel for multiple filters (color, type [face, photo, clipart, lineart]) and 
// splice the results.
canvas.images.get_google_images = function (query) {
    if (!query.strip()) {
        return new canvas.images.InfiniteSource();
    }
    
    function get_page (n) {
        var d = $.Deferred();
        jQuery.getJSON(
            "//ajax.googleapis.com/ajax/services/search/images?callback=?",
            {
                'resultFormat': 'text',
                'safe': 'moderate',
                'v': '1.0',
                'q': query,
                'rsz': '8',
                'start': n * 8
            })
            .done(function (response) {
                var items = $.map(response.responseData.results, function (result) {
                    return { content: new canvas.ForeignContent(result.tbUrl, result.width, result.height, result.url) };
                });
                d.resolveWith(null, [items]);
        });
        return d.promise();
    }

    var page = 4;
    function start () {
        var d = $.Deferred();
        return $.when.apply(undefined, $.map(Number.range(4), get_page))
            .done(function (resultsLists) {
                var results = [];
                $.each(arguments, function (i, resultList) {
                    results = $.merge(results, resultList);
                });
                d.resolveWith(null, [results]);
            }
        );
    }    
    
    function more () {
        if (page >= 8) {
            return $.when();
        }
        return get_page(page++);
    }
    
    return new canvas.images.InfiniteSource(start, more, "thumb");
};

canvas.images.PagedSource = Object.createSubclass();

canvas.images.PagedSource.prototype.init = function (source, page_size) {
    this._source = source;
    this._pages = [];
    this._buffer = [];
    this._page_size = page_size;
    this.current_page = 0;
};

canvas.images.PagedSource.prototype.start = function () {
    var self = this;
    var d = $.Deferred();
    this._source.start().done(function (items) {
        self._feed(items, d);
    });
    return d.promise();
};

canvas.images.PagedSource.prototype._try_resolve = function (deferred) {
    var next_page = this._pages[this.current_page+1];

    if (!next_page) {
        this._more(deferred);
        return;
    }

    var page = {
        previous: this.current_page > 0,
        next: next_page && next_page.length > 0,
        images: this._pages[this.current_page],
    }
    deferred.resolveWith(null, [page]);
};

canvas.images.PagedSource.prototype._feed = function (items, deferred) {
    Array.prototype.push.apply(this._buffer, items);

    if (this._buffer.length >= this._page_size || !items || items.length == 0) {
        this._pages.push(this._buffer.slice(0, this._page_size));
        this._buffer = this._buffer.slice(this._page_size);

        if (!items || items.length == 0) {
            this._pages.push([]);
        }
    }

    this._try_resolve(deferred);
};

canvas.images.PagedSource.prototype._more = function (deferred) {
    var self = this;
    this._source.more().done(function (items) {
        self._feed(items, deferred);
    });
};

canvas.images.PagedSource.prototype.next = function () {
    var d = $.Deferred();

    this.current_page += 1;
    this._try_resolve(d);

    return d.promise();
};

canvas.images.PagedSource.prototype.previous = function () {
    this.current_page -= 1;

    var d = $.Deferred();
    this._try_resolve(d);
    return d;
};

