remix.Easel = canvas.BaseWidget.createSubclass();

remix.Easel.prototype.init = function (root) {
    remix.Easel.__super__.init.apply(this, arguments);

    this.renderer = this.create_renderer(self);

    this.canvas_container = this.scoped('.canvas_container');

    this._mouse_down = false;
    this._mouse_on_easel = false;
    this._last_pt = { x: 0, y: 0 };
    this._fit_to_width = parseFloat(this.canvas_container.data('fit-to-width'));
    this._fit_to_height = parseFloat(this.canvas_container.data('fit-to-height'));

    this._wire_canvas();
};

remix.Easel.prototype.create_renderer = function () {
    return new remix.Renderer(
        this.scoped("canvas.output"),
        this.scoped(".layers canvas.foreground"),
        this.scoped(".layers canvas.background")
    );
};

remix.Easel.prototype._wire_canvas = function () {
    var canvas_ele = this.renderer.composite;
    var window_ele = canvas_ele.ultimate_parent();
    var self = this;

    function get_coord (evt) {
        var offset = canvas_ele.offset();
        return {x: Math.floor(evt.pageX - offset.left), y: Math.floor(evt.pageY - offset.top)};
    }

    this.canvas_container
        .bind('mouseenter', function (evt) {
            var pt = get_coord(evt);
            self.current_tool.enter(self._mouse_down, pt);
            self._last_pt = pt;
            self.mouse_on_easel = true;
        })
        .bind('mousedown', function (evt) {
            var pt = self._last_pt = get_coord(evt);
            self._mouse_down = true;
            self.root.addClass('noselect');
            document.onselectstart = function () { return false; }
            window_ele
                .one('mouseup', function (evt) {
                    self._mouse_down = false;
                    self.root.removeClass('noselect');
                    document.onselectstart = function () { return true; }
                    self.current_tool.up(self._last_pt);
                });
            self.current_tool.down(pt);
            evt.preventDefault();
        })
        .bind('mouseleave', function (evt) {
            var pt = get_coord(evt);
            self.current_tool.leave(self._mouse_down, pt);
            self.mouse_on_easel = false;
        });


    var canvas_dom_ele = canvas_ele.get(0);
    var brush_canvas_ele = $('#brush-canvas').get(0);
    window_ele.bind('mousemove', function (event) {
        if (event.target == canvas_dom_ele || event.target == brush_canvas_ele || self._mouse_down) {
            //trace('window', event);
            var next = get_coord(event);
            self.current_tool.move(self._mouse_down, self._last_pt, next);
            self._last_pt = next;
        }
    });
};

remix.Easel.prototype.load_content = function (content) {
    this.trigger('loading');
    var self = this;
    canvas.preload_image(content.original.url, function (image) {
        var size = util.fitInside(self._fit_to_width, self._fit_to_height, content.original);
        var options = {
            width: size.width,
            height: size.height,
            remix_of: content.id,
        };
        self._new(options);
        self.renderer.background.ctx().drawImage(image, 0,0, options.width, options.height);
        self.renderer.render(true);
        self.trigger('done_loading');
    });
};

remix.Easel.prototype._new = function (options) {
    this.trigger('loading');

    if (this.renderer) {
        this.renderer.finish_current_tool();
    }

    if (this._activity_timer) {
        this._activity_timer.stop();
    }

    this._activity_timer = new ActivityTimer(this.root, 30000);

    this._last_pt = {x: 0, y: 0};

    this.renderer.reset(options);

    this.renderer.resize(options.width, options.height);

    this.trigger('done_loading');
};

remix.Easel.prototype.cursor = function (style) {
    if (!style) {
        style = "default";
    }
    this.canvas_container.css('cursor', style);
};

remix.Easel.prototype.use_tool = function (tool, temporary) {
    this.current_tool = tool;

    if (!temporary) {
        this.renderer.use_tool(tool);
    }

    this.update_brush();

    if (this.mouse_on_easel) {
        this.current_tool.enter(this._mouse_down, this._last_pt);
    }

    this.renderer.render();

    // In-easel UI here (custom cursors, etc)
};

remix.Easel.prototype.flip = function (dimension) {
    var self = this;

    this.trigger('loading');

    this.renderer.finish_current_tool(false);

    var array = self.renderer.get_fliprotate_contexts();
    var each = function (i, ctx, done) {
        canvas.preload_image(ctx.canvas.toDataURL('image/png'), function (image) {
            remix.clear(ctx);
            ctx.save();

            if (dimension == 'h') {
                ctx.translate(image.width,0);
                ctx.scale(-1,1);
            } else {
                ctx.translate(0, image.height);
                ctx.scale(1,-1);
            }
            ctx.drawImage(image, 0,0);
            ctx.restore();
            done();
        });
    };

    var done = function () {
        self.renderer.render(true);
        self.trigger('done_loading');
    };

    util.scatterGather(array, each, done);
};

remix.Easel.prototype.rotate = function (direction) {
    this.trigger('loading');

    var self = this;

    self.renderer.finish_current_tool(false);

    var rotate_canvas = function (c, visible) {
        remix._resize(c, {width: c.height, height: c.width});
    }

    var array = self.renderer.get_fliprotate_contexts();

    var each = function (i, ctx, done) {
        canvas.preload_image(ctx.canvas.toDataURL('image/png'), function (image) {
            rotate_canvas(ctx.canvas);
            remix.clear(ctx);
            ctx.save();
            if (direction == 'cw') {
                ctx.rotate(Math.PI / 2);
                ctx.translate(0,-image.height);
            } else {
                ctx.rotate(-Math.PI / 2);
                ctx.translate(-image.width,0);
            }
            ctx.drawImage(image, 0,0);
            ctx.restore();
            done();
        });
    };

    var done = function () {
        rotate_canvas(self.renderer.composite[0]);
        self.renderer.render(true);
        $(self.scoped('.layers canvas.foreground')).trigger('done_loading');
        self.trigger('done_loading');
    }

    util.scatterGather(array, each, done);
};

remix.Easel.prototype.swap = function (checkpoint) {
    this.renderer.finish_current_tool(false);

    var fg = remix.save_canvas(this.renderer.foreground.ctx());
    var bg = remix.save_canvas(this.renderer.background.ctx());

    remix.restore_canvas(bg, this.renderer.foreground.ctx());
    remix.restore_canvas(fg, this.renderer.background.ctx());

    this.renderer.render(checkpoint);
};

remix.Easel.prototype.merge = function (checkpoint) {
    this.renderer.finish_current_tool(false);
    this.renderer.render(false, true);

    var comp = remix.save_canvas(this.renderer.composite.ctx());
    remix.restore_canvas(comp, this.renderer.background.ctx());
    remix.clear(this.renderer.foreground.ctx())

    this.renderer.render(checkpoint);
};

remix.Easel.prototype.update_brush = function () {
    if (this.renderer === undefined || this.current_tool === undefined) {
        return;
    }

    var Stroke = this.current_tool.Stroke;
    if (Stroke === undefined || Stroke.prototype.lineWidth === undefined) {
        return;
    }

    var c = remix.make_canvas_element(96,96);
    var ctx = c.ctx();
    ctx.fillStyle = remix.cssColor(Stroke.prototype.bgColor);
    ctx.fillRect(0,0, 96,96);
    var airbrush = new Stroke(ctx, this.current_tool.get_params);
    airbrush.pts = [ {x: 48, y: 48} ];
    airbrush.draw();
    this.scoped('img.brush_preview').attr("src", c.get(0).toDataURL('image/png'));

    var params = this.current_tool.get_params();

    var brush = this.scoped('canvas.brush_canvas');
    if (brush.length) {
        // TODO: In tests, no brush. Refactor this out of the test path and gut the if (brush.length) ... check
        var c =  params.line_width / 2;
        var cxy = remix.state.brush_radius = c+1;
        remix._resize(brush, {width: params.line_width + 2, height: params.line_width + 2})
        ctx = brush.ctx();
        remix.clear(ctx);
        ctx.beginPath();
        ctx.strokeStyle = "rgb(128,128,128)";
        ctx.strokeWidth = 1;
        if (params.square) {
            var half = params.line_width / 2;
            ctx.rect(cxy - half, cxy - half, params.line_width, params.line_width);
        } else {
            ctx.arc(cxy, cxy, c, 0, 2*Math.PI, true);
        }
        ctx.stroke();
    }
};

