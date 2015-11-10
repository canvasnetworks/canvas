/***********************
* Paint bucket
***********************/

remix.Fill = remix.createStroke("paintbucket",  "url(/static/img/remix-ui/fill-cursor.png) 20 20, auto");
remix.Fill.Tool.prototype.brush_preview = false;
remix.Fill.tolerance = 48;
remix.Fill.prototype.end = function (target) {
    var params = this.get_params();
    var w = this.ctx.canvas.width, h = this.ctx.canvas.height;
    var pixels = this.renderer.composite.ctx().getImageData(0,0, w,h);
    var fill_mask = this.ctx.createImageData(w,h);
    var pxd = pixels.data, fmd = fill_mask.data;

    var tstart = (target.y * w + target.x) * 4;
    var tR = pxd[tstart],
        tG = pxd[tstart+1],
        tB = pxd[tstart+2],
        tA = pxd[tstart+3];

    var abs = Math.abs;

    var T = params.tolerance;
    var iT = Math.floor(0xFF / T);

    var open = [[target.x, target.y]];
    while (open.length > 0) {
        var pt = open.shift();
        var px = pt[0], py = pt[1];
        var start = (py*w+px)*4;

        if (fmd[start+3] > 0) continue;

        var R = pxd[start],
            G = pxd[start+1],
            B = pxd[start+2],
            A = pxd[start+3];

        var dist =  abs(R - tR) + abs(G - tG) + abs(B - tB) + abs(A - tA);

        if (dist < T) {
            fmd[start+3] = 0xFF - dist*iT;

            if (px > 0) open.push([px - 1, py]);
            if (px < w-1) open.push([px + 1, py]);
            if (py > 0) open.push([px, py - 1]);
            if (py < h-1) open.push([px, py + 1]);
        }
    }

    var rc = params.knockout ? [0,0,0] : params.color.get_rgba8();
    var doodle_pixels = this.ctx.createImageData(w,h);
    var dpd = doodle_pixels.data;
    var alpha = Math.floor(params.alpha);
    for (var i = 0; i < fill_mask.data.length; i += 4) {
        if (fmd[i+3] > 0x00) {
            dpd[i] = rc[0];
            dpd[i+1] = rc[1];
            dpd[i+2] = rc[2];
            dpd[i+3] = alpha; //Math.floor(rc[3] * fmd[i+3] / 0xFF);
        }
    }
    this.tmp_canvas = remix.make_canvas_element(w,h);
    this.tmp_canvas.ctx().putImageData(doodle_pixels, 0,0)
};

remix.Fill.prototype.draw = function () {
    if (this.tmp_canvas) {
        this.ctx.globalCompositeOperation = this.get_params().knockout ? 'destination-out' : 'source-over';
        this.ctx.drawImage(this.tmp_canvas.get(0), 0,0);
    }
};

