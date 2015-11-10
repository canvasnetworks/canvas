remix.PointListTool = remix.Tool.createSubclass();

remix.PointListTool.prototype.init = function (renderer) {
    remix.PointListTool.__super__.init.apply(this, arguments);
    this.brush_canvas = $('#brush-canvas');
    this.renderer = renderer;
};

remix.PointListTool.prototype.brush_preview = true;

remix.PointListTool.prototype.enable_brush_preview = function (pt) {
    this.brush_preview = true;
    this.brush_canvas.show();
    var br = remix.state.brush_radius;
    this.brush_canvas.css({left: pt.x - br, top: pt.y - br});
};

remix.PointListTool.prototype.enter = function () {
    if (this.brush_preview) {
        this.brush_canvas.show();
    }
};

remix.PointListTool.prototype.leave = function () {
    if (this.brush_preview) {
        this.brush_canvas.hide();
    }
};

remix.PointListTool.prototype.down = function (pt) {
    this.stroke = new this.Stroke(this.renderer.foreground.ctx(), this.get_params, this);
    this.stroke.pts.push(pt);
    this.stroke.start(pt);
    this.renderer.render();
};

remix.PointListTool.prototype.render = function () {
    if (this.stroke) {
        this.stroke.draw();
    }
};

remix.PointListTool.prototype.move = function (mdown, pt_from, pt_to) {
    if (mdown) {
        this.stroke.pts.push(pt_to);
        this.stroke.move(pt_from, pt_to);
    }
    if (this.brush_preview) {
        var br = remix.state.brush_radius;
        this.brush_canvas.css({left: pt_to.x - br, top: pt_to.y - br});
    }
    this.renderer.render(); // Maybe move this into the mdown clause for perf?
};

remix.PointListTool.prototype.finalize = function (pt, done) {
    remix.PointListTool.__super__.finalize.apply(this, arguments);
    this.up(pt);
    if (!(done === false)) {
        if (this.brush_preview) {
            this.brush_canvas.hide();
        }
    }
};

remix.PointListTool.prototype.up = function (pt) {
    if (this.stroke) {
        this.stroke.end(pt);
        this.renderer.render(true);
        delete this.stroke;
    }
};

remix.PointListTool.prototype.shift_down = function() {
    if (this.stroke) {
        this.renderer.render(false);
    }
};

remix.PointListTool.prototype.shift_up = remix.PointListTool.prototype.shift_down;

remix.Stroke = Object.createSubclass();
remix.Stroke.prototype.init = function (ctx, parameter_provider, tool) {
    this.ctx = ctx || remix.state.ctx.doodle;
    this.get_params = parameter_provider;
    this.pts = [];
    if (tool && tool.renderer) {
        this.renderer = tool.renderer;
    }
};
remix.Stroke.prototype.start = function (pt) {}
remix.Stroke.prototype.move = function (pt1, pt2) {}
remix.Stroke.prototype.end = function () {}
remix.Stroke.prototype.draw = function () {}

remix.createStroke = function (name, cursor) {
    var Tool = remix.PointListTool.createSubclass();
    Tool.prototype.tool_name = Tool.tool_name = name; // Tool.tool_name used just for metadata, tokill?
    Tool.prototype.cursor = cursor;

    var Stroke = remix.Stroke.createSubclass();
    Tool.Stroke = Tool.prototype.Stroke = Stroke; // TODO: Ditch Tool.Stroke for Tool.prototype.Stroke
    Stroke.Tool = Tool;
    return Stroke;
};



/***********************
* Airbrush
***********************/

remix.Airbrush = remix.createStroke("airbrush", "url(/static/img/remix-ui/draw-crosshair.png) 4 4, auto");

remix.Airbrush.prototype.lineWidth = 6;
remix.Airbrush.prototype.shadowBlur = 0;
remix.Airbrush.prototype.bgColor = [255,255,255];

remix.Airbrush.prototype.draw = function () {
    var params = this.get_params();

    this.ctx.shadowColor = params.color.get_css();
    this.ctx.shadowOffsetX = this.ctx.shadowOffsetY = 1500;
    this.ctx.shadowBlur = params.shadow_blur;
    this.ctx.miterLimit = 100000;

    this.ctx.translate(-1500,-1500);

    if (this.pts.length == 1) {
        // Dot
        this.ctx.fillStyle = params.color.get_css();
        this.ctx.beginPath();
        if (params.square) {
            this.ctx.rect(this.pts[0].x - (params.line_width / 2), this.pts[0].y - (params.line_width / 2), params.line_width, params.line_width);
        } else {
            this.ctx.arc(this.pts[0].x, this.pts[0].y, params.line_width / 2, 0, 2 * Math.PI, true);
        }
        this.ctx.closePath();
        this.ctx.fill();

    } else if (this.pts.length > 1) {
        // Line
        this.ctx.strokeStyle = params.color.get_css();
        var old_line_width = this.ctx.lineWidth;

        this.ctx.lineJoin = this.ctx.lineCap = "round";
        this.ctx.lineWidth = params.line_width;

        if (remix._shift_down || (!params.square && this.pts.length == 2)) {
            this.ctx.beginPath();
            this.ctx.moveTo(this.pts[0].x, this.pts[0].y);
            var last_pt = this.pts[this.pts.length - 1];
            this.ctx.lineTo(last_pt.x, last_pt.y);
            if (params.square) {
                this.ctx.lineJoin = "miter";
                this.ctx.lineCap = "square";
            }
            this.ctx.stroke();
        } else {
            if (!params.square) {
                this.ctx.beginPath();
                this.ctx.moveTo(this.pts[0].x, this.pts[0].y);
                var bezier_path = remix.Airbrush.catmullrom_to_bezier(this.pts);
                for (var i = 0; i < bezier_path.length; ++i) {
                    this.ctx.bezierCurveTo.apply(this.ctx, bezier_path[i]);
                }
                this.ctx.stroke();
            } else {

                for(var i = 0; i < this.pts.length; i++) {
                    var pt = this.pts[i];
                    this.ctx.beginPath();
                    this.ctx.rect(pt.x - (params.line_width / 2), pt.y - (params.line_width / 2), params.line_width, params.line_width);
                    this.ctx.closePath();
                    this.ctx.fill();
                }

                var half = params.line_width / 2;

                this.ctx.lineJoin = "miter";
                this.ctx.lineCap = "square";
                this.ctx.lineWidth = old_line_width;

                // this is kind of stupid, but works and doesn't havee all the
                // inherent problems with drawing beziers of varying widths
                for(var i = 0; i < this.pts.length - 1; i++) {
                    var pt0 = this.pts[i];
                    var pt1 = this.pts[i+1];

                    this.ctx.beginPath();
                    this.ctx.moveTo(pt0.x - half, pt0.y - half);
                    this.ctx.lineTo(pt0.x + half, pt0.y - half);
                    this.ctx.lineTo(pt1.x + half, pt1.y - half);
                    this.ctx.lineTo(pt1.x - half, pt1.y - half);
                    this.ctx.stroke();
                    this.ctx.closePath();
                    this.ctx.fill();

                    this.ctx.beginPath();
                    this.ctx.moveTo(pt0.x + half, pt0.y - half);
                    this.ctx.lineTo(pt0.x + half, pt0.y + half);
                    this.ctx.lineTo(pt1.x + half, pt1.y + half);
                    this.ctx.lineTo(pt1.x + half, pt1.y - half);
                    this.ctx.stroke();
                    this.ctx.closePath();
                    this.ctx.fill();

                    this.ctx.beginPath();
                    this.ctx.moveTo(pt0.x + half, pt0.y + half);
                    this.ctx.lineTo(pt0.x - half, pt0.y + half);
                    this.ctx.lineTo(pt1.x - half, pt1.y + half);
                    this.ctx.lineTo(pt1.x + half, pt1.y + half);
                    this.ctx.stroke();
                    this.ctx.closePath();
                    this.ctx.fill();

                    this.ctx.beginPath();
                    this.ctx.moveTo(pt0.x - half, pt0.y + half);
                    this.ctx.lineTo(pt0.x - half, pt0.y - half);
                    this.ctx.lineTo(pt1.x - half, pt1.y - half);
                    this.ctx.lineTo(pt1.x - half, pt1.y + half);
                    this.ctx.stroke();
                    this.ctx.closePath();
                    this.ctx.fill();
                }
            }
        }
    }
};

remix.Airbrush.catmullrom_to_bezier = function ( points ) {
    /* Inspired by http://schepers.cc/svg/path/catmullrom2bezier.js */
    var bezier_path = [];
    for (var i = 0, iLen = points.length; iLen - 1 > i; i++) {
        var p;
        if ( 0 == i ) {
            p = [points[i], points[i], points[i+1], points[i+2]];
        } else if ( iLen - 2 == i ) {
            p = [points[i-1], points[i], points[i+1], points[i+1]];
        } else {
            p = [points[i-1], points[i], points[i+1], points[i+2]];
        }

        // Catmull-Rom to Cubic Bezier conversion matrix
        //      0     1     0     0
        //   -1/6     1   1/6     0
        //      0   1/6     1  -1/6
        //      0     0     1     0

        bezier_path.push([
           ((-p[0].x + 6*p[1].x + p[2].x) / 6), ((-p[0].y + 6*p[1].y + p[2].y) / 6),
           (( p[1].x + 6*p[2].x - p[3].x) / 6), (( p[1].y + 6*p[2].y - p[3].y) / 6),
           p[2].x, p[2].y
        ]);

    }

    return bezier_path;
}



/***********************
* Eraser
***********************/

remix.Eraser = remix.createStroke("eraser", "url(/static/img/remix-ui/erase-crosshair.png) 4 4, auto");

remix.Eraser.prototype.lineWidth = 12;
remix.Eraser.prototype.shadowBlur = 4;
remix.Eraser.prototype.bgColor = [0,0,0,255];

remix.Eraser.prototype.draw = function () {
    // Should be inheritance
    this.ctx.globalCompositeOperation = 'destination-out';
    remix.Airbrush.prototype.draw.call(this);
};



/***********************
* Clone
***********************/

remix.Clone = remix.createStroke("clone", "url(/static/img/remix-ui/clone-crosshair.png) 11 11, auto");

remix.Clone.Tool.prototype.brush_preview = false;

remix.Clone.prototype.init = function (ctx, pp, tool) {
    remix.Clone.__super__.init.apply(this, arguments);
    this.pts = [];
    this.mask_canvas = remix.make_canvas_element(this.ctx.canvas.width, this.ctx.canvas.height);
    this.tool = tool;

    var _get_params = this.get_params;
    this.get_params = function () {
        var params = _get_params();
        params.color.set_alpha(params['alpha']);
        return params;
    }

};

// Closure generated function, so I can't just call a parent method and I'm about to shadow this guy
remix.Clone.Tool.prototype.original_down = remix.Clone.Tool.prototype.down;
remix.Clone.Tool.prototype.original_move = remix.Clone.Tool.prototype.move;
remix.Clone.Tool.prototype.original_finalize = remix.Clone.Tool.prototype.finalize;

remix.Clone.Tool.prototype.update_crosshair = function (pt) {
    this.crosshair.css({left: pt.x - this.delta.x - 11, top: pt.y - this.delta.y - 11});
};

remix.Clone.Tool.prototype.to_draw_crosshair = function () {
    this.get_cursor_method()("url(/static/img/remix-ui/draw-crosshair.png) 4 4, auto");
};

remix.Clone.Tool.prototype.back_to_crosshair = function () {
    this.crosshair.hide();
    this.get_cursor_method()("url(/static/img/remix-ui/clone-crosshair.png) 11 11, auto");
    return 'start';
};

remix.Clone.Tool.prototype.show_crosshair = function () {
    if (!this.crosshair) {
        this.crosshair = this.easel.scoped('.clone_crosshair');
    }
    this.crosshair.show();
};

remix.Clone.Tool.prototype.modes = {
    start: {
        alt_up: function () {
            // Go back to the mode you came from, because you didn't click.
            if (this.pick_pt) {
                this.enable_brush_preview(remix.state.last);
                this.to_draw_crosshair();
                this.show_crosshair();
                if (this.place_pt) {
                    return 'clone';
                }
                return 'place';
            }
        },
        up: function (pt) {
            if (pt) {
                this.pick_pt = pt;
                this.to_draw_crosshair();
                this.enable_brush_preview(pt);
                this.show_crosshair();
                this.delta = {x: 0, y: 0};
                this.update_crosshair(pt);
            }
            return 'place';
        }
    },
    place: {
        alt_down: remix.Clone.Tool.prototype.back_to_crosshair,
        move: remix.Clone.Tool.prototype.move,
        down: function (pt) {
            this.place_pt = pt;
            this.delta = {x: this.place_pt.x - this.pick_pt.x, y: this.place_pt.y - this.pick_pt.y};

            var source_orig = this.renderer.composite.get(0);
            this.source = remix.make_canvas_element(source_orig.width, source_orig.height);
            this.source.ctx().drawImage(source_orig, this.delta.x, this.delta.y);
            remix.Clone.Tool.prototype.original_down.call(this, pt);
            this.update_crosshair(pt);
            return "clone";
        }
    },
    clone: {
        alt_down: remix.Clone.Tool.prototype.back_to_crosshair,
        down: remix.Clone.Tool.prototype.down,
        move: function (mdown, pt_from, pt_to) {
            remix.Clone.Tool.prototype.original_move.call(this, mdown, pt_from, pt_to);
            this.update_crosshair(pt_to);
        },
        up: remix.Clone.Tool.prototype.up,
    }
};

remix.Clone.Tool.prototype.finalize = function (pt, done) {
    remix.Clone.Tool.__super__.finalize.apply(this, arguments);
    if (this.crosshair) {
        this.crosshair.hide();
    }
};

Mode.delegates(remix.Clone.Tool.prototype, 'up', 'down', 'move', 'alt_down', 'alt_up');

remix.Clone.prototype.lineWidth = 12;
remix.Clone.prototype.shadowBlur = 4;
remix.Clone.prototype.bgColor = [255,255,255];

remix.Clone.prototype.draw = function () {
    if (this.tool && this.tool.pick_pt && this.tool.place_pt) {
        this.draw_mask();
        this.fill_mask();
        this.ctx.drawImage(this.mask_canvas.get(0), 0, 0);
    }
};

remix.Clone.prototype.draw_mask = function () {
    var out = this.ctx;
    this.ctx = this.mask_canvas.ctx();
    this.ctx.save();
    remix.clear(this.ctx);
    remix.Airbrush.prototype.draw.call(this);
    this.ctx.restore();
    this.ctx = out;
};

remix.Clone.prototype.fill_mask = function () {
    var ctx = this.mask_canvas.ctx();
    ctx.save();
    ctx.globalCompositeOperation = 'source-in';
    ctx.drawImage(this.tool.source.get(0), 0,0);
    ctx.restore();
};

remix.Clone.Tool.prototype.stroke_down = remix.Clone.Tool.prototype.down;
remix.Clone.Tool.prototype.down = function (pt) {
    if (this.source_pt) {
        return this.stroke_down(pt);
    } else {
        this.source_pt = pt;
    }
};
