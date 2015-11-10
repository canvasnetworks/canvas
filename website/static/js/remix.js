remix = {};
remix.panels = {};
remix.pickers = {};
remix.state = {}; // Need to kill
remix._shift_down = false;

remix.save_canvas = function (ctx) {
    return ctx.getImageData(0,0, ctx.canvas.width, ctx.canvas.height);
};

remix.restore_canvas = function (image_data, ctx, noresize) {
    if (ctx.canvas.width != image_data.width || ctx.canvas.height != image_data.height) {
        remix._resize(ctx.canvas, image_data);
    }
    ctx.putImageData(image_data, 0,0);
};

remix.clear = function (ctx) {
    ctx.clearRect(0,0, ctx.canvas.width, ctx.canvas.height);
};

remix.getRGB888 = function (color) {
    var jsc = color.rgb;
    return [jsc[0] * 255, jsc[1] * 255, jsc[2] * 255];
};

remix.asset = function (src) {
    var i = new Image();
    i.src = src;
    return i;
};

remix.dist2 = function (pta, ptb) {
    var dx = ptb.x - pta.x,
        dy = ptb.y - pta.y;
    return dx * dx + dy * dy;
};

remix.dist = function (pta, ptb) {
    return Math.sqrt(remix.dist2(pta, ptb));
};

remix._resize = function (sel, size) {
    var ele = $(sel).get(0);
    ele.width = size.width;
    ele.height = size.height;
};

remix.cssColor = function (rgba) {
    if (rgba.length == 3) {
        return "rgb(" +  Math.floor(rgba[0]) + "," + Math.floor(rgba[1]) + "," + Math.floor(rgba[2]) + ")";
    }
    return "rgba(" + Math.floor(rgba[0]) + "," + Math.floor(rgba[1]) + "," + Math.floor(rgba[2]) + "," + (Math.floor(rgba[3]) / 0xFF) + ")";
};

remix.make_canvas_element = function (width, height) {
    return $('<canvas width="' + width + '" height="' + height + '"></canvas>');
};

