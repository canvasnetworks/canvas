remix.Rect = function (pt, size) {
    this.x = pt.x;
    this.y = pt.y;
    this.width = size.width;
    this.height = size.height;
};

remix.Rect.centeredRect = function (pt, size) {
    return new remix.Rect({x: pt.x - size.width / 2, y: pt.y - size.height / 2}, size);
};

remix.Rect.prototype.containsPoint = function (pt) {
    return pt.x > this.x && pt.x <= this.x + this.width &&
        pt.y > this.y && pt.y <= this.y + this.height;
};

remix.Rect.prototype.center = function () { return {x: this.x + this.width/2, y: this.y + this.height / 2}; };

remix.Rect.prototype.ul = function () { return {x: this.x, y: this.y }; };
remix.Rect.prototype.lr = function () { return {x: this.x + this.width, y: this.y + this.height }; };
remix.Rect.prototype.ur = function () { return {x: this.x + this.width, y: this.y }; };
remix.Rect.prototype.ll = function () { return {x: this.x, y: this.y + this.height }; };

remix.Rect.prototype.uc = function () { return {x: this.x + this.width / 2, y: this.y }; };
remix.Rect.prototype.lc = function () { return {x: this.x + this.width / 2, y: this.y + this.height }; };
remix.Rect.prototype.cl = function () { return {x: this.x, y: this.y + this.height / 2 }; };
remix.Rect.prototype.cr = function () { return {x: this.x + this.width, y: this.y + this.height / 2 }; };

remix.Rect.prototype.size = function () { return Math.sqrt(this.width * this.width + this.height * this.height); };

remix.Rect.index_from_radians = function (rads) {
    while (rads < 0) {
        rads += Math.PI * 2;
    }
    return Math.round(rads / Math.PI / 2 * 8) % 8;
};

remix.Rect.points = ['uc', 'ur', 'cr', 'lr', 'lc', 'll', 'cl', 'ul'];
remix.Rect.compass = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
remix.Rect.cardinal = {'N': true, 'W': true, 'S': true, 'E': true };


// Base class for Stamp and Text.
remix.Stampable = remix.Tool.createSubclass();
remix.Stampable.prototype.init = function () {
    remix.Stampable.__super__.init.apply(this, arguments);
    this.mode = 'new';
    this.rot = 0;
    this.mirrored = false;
    this.flipped = false;
    this.update_on_finalize = false;
};

remix.Stampable.dv = remix.asset("/static/img/dashed_vertical.png");
remix.Stampable.dh = remix.asset("/static/img/dashed_horizontal.png");

remix.Stampable.prototype.rad = function (pt) {
    center = this.rect.center();
    var dy = center.y - pt.y,
        dx = center.x - pt.x;
    return -Math.atan2(dx,dy);
};

remix.Stampable.prototype.invert_rot = function (pt) {
    var center = this.rect.center();
    var rot = this.rad(pt) - this.rot;
    var dist = remix.dist(center, pt);
    return { x: center.x + Math.sin(rot) * dist, y: center.y - Math.cos(rot) * dist };
};

remix.Stampable.prototype.set_rotate_cursor = function (pt) {
    this.get_cursor_method()('url(/static/img/remix-ui/rotate-' + remix.Rect.compass[remix.Rect.index_from_radians(this.rad(pt))] + '.png), auto');
};

remix.Stampable.prototype.minimum_width = function () { return 0; }

remix.Stampable.prototype.snap_to_delta = 12;

remix.Stampable.prototype.modes = {
    'new': {
        place: function () {
            var size = this.renderer.size();
            var rect = new remix.Rect({x: 0, y: 0}, util.fitInside(size.width * 0.9, size.height * 0.9, this.src_rect));
            this.center({x: size.width/2, y: size.height/2}, rect);
            this.rot = 0;
            this.mode = 'placing'; // Instant switch before render
            this.update_on_finalize = true;

            this.renderer.render();
        }
    },
    'placing': {
        down: function (orig_pt) {
            var pt = this.invert_rot(orig_pt);
            if (this.rect.containsPoint(pt)) {
                this.offset = {x: this.rect.x - orig_pt.x, y: this.rect.y - orig_pt.y};
                return 'dragging';
            } else if (this.pickCorner(pt) != -1) {
                this.corner = this.pickCorner(pt);
                this.resize_pt = pt;
                this.resize_rect = new remix.Rect(this.rect, this.rect);
                this.resize_ratio = this.rect.size() / remix.dist(pt, this.rect.center());
                this._starting_compass = remix.Rect.compass[this.corner];
                this._starting_mirrored = this.mirrored;
                this._starting_flipped = this.flipped;
                return 'resizing';
            } else {
                this.rot_start = this.rot - this.rad(orig_pt);
                return 'rotating';
            }
        },
        move: function (_, __, orig_pt) {
            var pt = this.invert_rot(orig_pt);
            if (this.rect.containsPoint(pt)) {
                this.get_cursor_method()('move');
            } else if (this.pickCorner(pt) != -1) {
                var pick = this.pickCorner(pt);
                // Pick a north
                this.get_cursor_method()(remix.Rect.compass[(remix.Rect.index_from_radians(this.rot) + pick) % 8] + '-resize');
            } else {
                this.set_rotate_cursor(orig_pt);
            }
        },
    },
    'rotating': {
        up: Mode.transition('placing'),
        move: function (_, __, pt) {
            this.rot = this.rad(pt) + this.rot_start;
            this.set_rotate_cursor(pt);
            this.renderer.render();
        }
    },
    'dragging': {
        up: Mode.transition('placing'),
        move: function (_, __, pt) {
            this.rect.x = pt.x + this.offset.x;
            this.rect.y = pt.y + this.offset.y;
            this.renderer.render();
        }
    },
    'resizing': {
        up: Mode.transition('placing'),
        move: function (_, __, orig_pt) {
            var pt = this.invert_rot(orig_pt);
            var compass = remix.Rect.compass[this.corner];
            var cardinal = remix.Rect.cardinal[compass];
            var center = this.rect.center();
            if (!cardinal) {
                // Keep aspect ratio, change the size of the object
                var dist = remix.dist(pt, center) * this.resize_ratio;
                var old_size = this.rect.size();

                var width = Math.max(this.minimum_width(), (this.rect.width / old_size * dist));

                var size = {width: width, height: this.rect.height / old_size * dist};
                this.rect = remix.Rect.centeredRect(center, size);
            } else {
                // Only resize horiz or vert, change aspect ratio
                if (compass == 'N' || compass == 'S') {
                    var start_height = this.resize_rect.height;
                    var new_height = 2 * Math.abs(this.resize_rect.center().y - pt.y);
                    var delta = new_height - start_height;
                    var height = delta + this.resize_rect.height;
                    if (Math.abs(delta) < this.snap_to_delta && !remix._alt_down) {
                        height = start_height;
                    }
                    this.rect = remix.Rect.centeredRect(center, { width: this.rect.width, height: height });
                } else {
                    var start_width = this.resize_rect.width;
                    var new_width = 2 * Math.abs(this.resize_rect.center().x - pt.x);
                    var delta = new_width - start_width;
                    if (Math.abs(delta) < this.snap_to_delta && !remix._alt_down) {
                        new_width = start_width;
                    }
                    var width = Math.max(this.minimum_width(), new_width);
                    this.rect = remix.Rect.centeredRect(center, { width: width, height: this.rect.height });
                }
            }

            // Check mirroring and flipping.
            this.mirrored = (
                this._starting_compass === 'W' && pt.x > this.resize_rect.center().x ||
                this._starting_compass === 'E' && pt.x < this.resize_rect.center().x
            );
            this.mirrored = this._starting_mirrored != this.mirrored;
            this.flipped = (
                this._starting_compass === 'N' && pt.y > this.resize_rect.center().y ||
                this._starting_compass === 'S' && pt.y < this.resize_rect.center().y
            );
            this.flipped = this._starting_flipped != this.flipped;

            this.renderer.render();
        },
    },
};

remix.Stampable.prototype.center = function (pt, rect) {
    this.rect = new remix.Rect({x: pt.x - rect.width/2, y: pt.y - rect.height/2}, rect);
    this.offset = {x: -this.rect.width/2, y: -this.rect.height/2};
};

Mode.delegates(remix.Stampable.prototype, 'place', 'up', 'down', 'move');

remix.Stampable.prototype.preview = function () {
    if (this.mode == 'new') return;
    this.draw(this.renderer.composite.ctx()); // TOKILL
};

remix.Stampable.prototype.draw_ui = function () {
    if (this.mode == 'new') return;
    var ctx = this.renderer.composite.ctx();
    ctx.save();
    var ph = ctx.createPattern(remix.Stampable.dh, "repeat");
    var pv = ctx.createPattern(remix.Stampable.dv, "repeat");

    this.rotate(ctx);
    ctx.fillStyle = ph;
    ctx.fillRect(this.rect.x, this.rect.y - 1, this.rect.width, 2);
    ctx.fillRect(this.rect.x, this.rect.y + this.rect.height - 1, this.rect.width, 2);

    ctx.fillStyle = pv;
    ctx.fillRect(this.rect.x - 1, this.rect.y, 2, this.rect.height);
    ctx.fillRect(this.rect.x + this.rect.width - 1, this.rect.y, 2, this.rect.height);

    ctx.fillStyle = "rgba(255,255,255,0.9)";
    var sz = 6;
    var hsz = sz/2;
    for (var i = 0; i < this.pick_points.length; ++i) {
        var pt = this.rect[this.pick_points[i]]();
        ctx.fillRect(pt.x - hsz, pt.y - hsz, sz, sz);
        ctx.strokeRect(pt.x - hsz, pt.y - hsz, sz, sz);
    }

    ctx.restore();
};

remix.Stampable.prototype.rotate = function (ctx) {
    var center = this.rect.center();
    ctx.translate(center.x, center.y);
    ctx.rotate(this.rot);
    ctx.translate(-center.x, -center.y);
};

remix.Stampable.prototype.mirror = function (ctx) {
    var center = this.rect.center();
    ctx.translate(center.x, center.y);
    ctx.scale(-1,1);
    ctx.translate(-center.x, -center.y);
};

remix.Stampable.prototype.flip = function (ctx) {
    var center = this.rect.center();
    ctx.translate(center.x, center.y);
    ctx.scale(1,-1);
    ctx.translate(-center.x, -center.y);
};

remix.Stampable.prototype.draw = function (ctx) {
    ctx.save();
    this.rotate(ctx);
    var w = this.renderer.composite.width();
    var h = this.renderer.composite.height();
    if (this.mirrored) {
        this.mirror(ctx);
    }
    if (this.flipped) {
        this.flip(ctx);
    }
    ctx.globalAlpha = this.get_params().alpha / 255.0;
    ctx.drawImage(
        this.image,
        this.src_rect.x, this.src_rect.y,
        this.src_rect.width, this.src_rect.height,
        this.rect.x, this.rect.y,
        this.rect.width, this.rect.height);
    ctx.restore();
};

remix.Stampable.prototype.set_image = function (stamp, content) {
    this.image = stamp;
    this.content = content;
    this.src_rect = new remix.Rect({x: 0, y: 0}, {width: stamp.width, height: stamp.height});
};

remix.Stampable.prototype.finish = function () {
    if (this.mode != 'new') {
        this.draw(this.renderer.foreground.ctx());
        this.mode = 'new';
        this.record_metadata();
        this.renderer.render(true);
    } else {
        this.renderer.render();
    }
    this.get_cursor_method()('default');
    this.mode = 'new';
    this.update_on_finalize = false;
};

remix.Stampable.prototype.record_metadata = function () {};

remix.Stampable.prototype.pick_points = remix.Rect.points;

remix.Stampable.prototype.pickCorner = function (pickPoint) {
    var hit_dist2 = 20*20,
        closest = 0,
        closest_dist2 = Infinity;
    for (var i = 0; i < this.pick_points.length; ++i) {
        var pt = this.rect[this.pick_points[i]]();
        var d = remix.dist2(pt, pickPoint);
        if (d < closest_dist2) {
            closest_dist2 = d;
            closest = i;
        }
    }

    if (closest_dist2 > hit_dist2) {
        return -1;
    } else {
        return remix.Rect.points.indexOf(this.pick_points[closest]);
    }
};

remix.Stampable.prototype.finalize = function () {
    remix.Stampable.__super__.finalize.apply(this, arguments);
    this.finish();
};

remix.tmp_canvas = function () {
    return $("<canvas></canvas>");
};



/***********************
* Stamp
***********************/

remix.Stamp = remix.Stampable.createSubclass();
remix.Stamp.prototype.modes = $.extend(true, {}, remix.Stampable.prototype.modes);

remix.Stamp.prototype.record_metadata = function () {
    if (this.content) {
        var used_stamps = this.renderer.metadata.used_stamps;
        for (var i = 0; i < used_stamps.length; ++i) {
            if (used_stamps[i] == this.content.id) {
                return;
            }
        }
        used_stamps.push(this.content.id);
    }
};


remix.StampLibrary = remix.Stamp.createSubclass();

remix.StampLibrary.prototype.init = function () {
    this.tool_name = 'stamps';
    remix.StampLibrary.__super__.init.apply(this, arguments);
};

remix.StampLibrary.tool_name = 'stamp-library';


remix.StampUpload = remix.Stamp.createSubclass();

remix.StampUpload.prototype.init = function () {
    this.tool_name = 'upload';
    remix.StampUpload.__super__.init.apply(this, arguments);
};

remix.StampUpload.tool_name = 'stamp-upload';

