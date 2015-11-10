remix.DragTool = remix.Tool.createSubclass();

remix.DragTool.prototype.init = function (renderer, parameter_provider) {
    remix.DragTool.__super__.init.apply(this, arguments);
    this.renderer = renderer;
    this.get_params = parameter_provider;
};

remix.DragTool.prototype.down = function (pt) {
    this.first = pt;
};

remix.DragTool.prototype.move = function (mdown, a, b) {
    this.second = b;
    this.renderer.render();
};

remix.DragTool.prototype.up = function (pt) {
    this.second = pt;
    this.renderer.render(true);
    this.first = this.second = false;
};

remix.DragTool.prototype.render = function (ctx) {
    if (this.first && this.second) {
        this.draw(ctx);
    }
};

remix.Rectangle = remix.DragTool.createSubclass();
remix.Rectangle.tool_name = "rectangle";
remix.Rectangle.prototype.init = function () {
    remix.Rectangle.__super__.init.apply(this, arguments);
    this.tool_name = remix.Rectangle.tool_name;
};

remix.Rectangle.prototype.cursor = "url(/static/img/remix-ui/crosshair.png) 7 7, auto";

remix.Rectangle.prototype.draw = function (ctx) {
    ctx.fillStyle = this.get_params().color.get_css()
    ctx.beginPath();
    var second = this.second;
    if (remix._shift_down) {
        var deltaX = this.second.x - this.first.x;
        var deltaY = this.second.y - this.first.y;
        var distance = Math.min(Math.abs(deltaX), Math.abs(deltaY));
        second.x = this.first.x + distance * (second.x > this.first.x ? 1 : -1);
        second.y = this.first.y + distance * (second.y > this.first.y ? 1 : -1);
    }
    ctx.moveTo(this.first.x, this.first.y);
    ctx.lineTo(second.x, this.first.y);
    ctx.lineTo(second.x, second.y);
    ctx.lineTo(this.first.x, second.y);
    ctx.lineTo(this.first.x, this.first.y);
    ctx.fill();
};

remix.Circle = remix.DragTool.createSubclass();
remix.Circle.tool_name = "circle";
remix.Circle.prototype.init = function () {
    remix.Circle.__super__.init.apply(this, arguments);
    this.tool_name = remix.Circle.tool_name;
};

remix.Circle.prototype.cursor = "url(/static/img/remix-ui/crosshair.png) 7 7, auto";

remix.Circle.prototype.draw = function (ctx) {
    ctx.fillStyle = this.get_params().color.get_css()
    var distX = Math.abs(this.second.x-this.first.x);
    var distY = Math.abs(this.second.y-this.first.y);
    var radius = Math.sqrt(Math.pow(distX,2) + Math.pow(distY,2));
    var scale = [1, 1];
    if (!remix._shift_down) {
        if (distX < distY) {
            scale[0] = distX/distY || 0.001;
        } else {
            scale[1] = distY/distX || 0.001;
        }
    }
    ctx.scale(scale[0], scale[1]);
    ctx.beginPath();
    ctx.arc(this.first.x/scale[0], this.first.y/scale[1], radius, 0, 2 * Math.PI, false);
    ctx.fill();
};


remix.Shape = remix.DragTool.createSubclass();
remix.Shape.prototype.cursor = "url(/static/img/remix-ui/crosshair.png) 7 7, auto";
remix.Shape.shapes = {};

remix.Shape.prototype.draw = function (ctx) {
    var params = this.get_params();
    remix.Shape.shapes[params.shape](ctx, params, this.first, this.second, remix._shift_down);
}

remix.Shape.shapes.rectangle = function (ctx, params, first, second, constrained) {
    ctx.fillStyle = params.color.get_css();
    ctx.beginPath();
    if (constrained) {
        var deltaX = second.x - first.x;
        var deltaY = second.y - first.y;
        var distance = Math.min(Math.abs(deltaX), Math.abs(deltaY));
        second.x = first.x + distance * (second.x > first.x ? 1 : -1);
        second.y = first.y + distance * (second.y > first.y ? 1 : -1);
    }
    ctx.moveTo(first.x, first.y);
    ctx.lineTo(second.x, first.y);
    ctx.lineTo(second.x, second.y);
    ctx.lineTo(first.x, second.y);
    ctx.lineTo(first.x, first.y);
    ctx.fill();
};


remix.Shape.shapes.ellipse = function (ctx, params, first, second, constrained) {
    ctx.fillStyle = params.color.get_css();
    var distX = Math.abs(second.x-first.x);
    var distY = Math.abs(second.y-first.y);
    var radius = Math.sqrt(Math.pow(distX,2) + Math.pow(distY,2));
    var scale = [1, 1];
    if (!remix._shift_down) {
        if (distX < distY) {
            scale[0] = distX/distY || 0.001;
        } else {
            scale[1] = distY/distX || 0.001;
        }
    }
    ctx.scale(scale[0], scale[1]);
    ctx.beginPath();
    ctx.arc(first.x/scale[0], first.y/scale[1], radius, 0, 2 * Math.PI, false);
    ctx.fill();
};

remix.Shape.shapes.line = function (ctx, params, first, second, constrained) {
    ctx.lineWidth = params.line_width;
    ctx.miterLimit = 100000;
    ctx.lineCap = "round";
    ctx.strokeStyle = params.color.get_css();

    ctx.beginPath();
    ctx.moveTo(first.x, first.y);
    ctx.lineTo(second.x, second.y);
    ctx.stroke();
}