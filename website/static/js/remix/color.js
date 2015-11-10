remix.Color = Object.createSubclass();

remix.Color.prototype.init = function (rgba) {
    this.rgba = rgba;
    this._hue = null; // Defaults to whatever we derive from rgba.
    if (this.rgba.length === 3) {
        this.rgba.push(255); // Default to fully opaque.
    }
};

remix.Color.hsv_to_rgb = function (hsv) {
    // Credit to http://mjijackson.com/
    var h = hsv[0],
        s = hsv[1],
        v = hsv[2],
        r, g, b;

    var i = Math.floor(h * 6);
    var f = h * 6 - i;
    var p = v * (1 - s);
    var q = v * (1 - f * s);
    var t = v * (1 - (1 - f) * s);

    switch (i % 6) {
        case 0: r = v, g = t, b = p; break;
        case 1: r = q, g = v, b = p; break;
        case 2: r = p, g = v, b = t; break;
        case 3: r = p, g = q, b = v; break;
        case 4: r = t, g = p, b = v; break;
        case 5: r = v, g = p, b = q; break;
    }
    
    return [r * 255, g * 255, b * 255];
};

remix.Color.from_hsv = function (hsv) {
    var color = new remix.Color(remix.Color.hsv_to_rgb(hsv));
    color._hue = hsv[0];
    return color;
};

remix.Color.prototype.equals = function (other) {
    return this.rgba[0] == other.rgba[0] &&
           this.rgba[1] == other.rgba[1] &&
           this.rgba[2] == other.rgba[2] &&
           this.rgba[3] == other.rgba[3];
};

remix.Color.prototype.copy = function () {
    var color = new remix.Color(this.rgba.slice());
    color._hue = this._hue;
    return color;
};

remix.Color.prototype.get_hex = function () {
    // Disregards opacity.
    function dec_to_hex (d) {
        d = Math.round(d);
        var hex = Number(d).toString(16);
        while (hex.length < 2) {
            hex = '0' + hex;
        }
        return hex.toUpperCase();
    }
    return dec_to_hex(this.rgba[0]) + dec_to_hex(this.rgba[1]) + dec_to_hex(this.rgba[2]);
};

remix.Color.prototype.get_css = function () {
    var rgba = $.map(this.rgba, Math.floor);
    return $.format("rgba({0}, {1}, {2}, {3})", rgba[0], rgba[1], rgba[2], rgba[3] / 255);
};

remix.Color.prototype.get_rgb = function () {
    return this.rgba.slice(0, 3);
};

remix.Color.prototype.get_hsv = function () {
    var rgb = $.map(this.get_rgb(), function (val) {
        return val / 255;
    });
    var r = rgb[0], g = rgb[1], b = rgb[2];

    var max = Math.max(r, g, b), min = Math.min(r, g, b);

    var h, s, v = max;

    var d = max - min;
    s = max == 0 ? 0 : d / max;

    if (max == min) {
        h = 0; // achromatic
    } else {
        switch (max) {
            case r: h = (g - b) / d + (g < b ? 6 : 0); break;
            case g: h = (b - r) / d + 2; break;
            case b: h = (r - g) / d + 4; break;
        }
        h /= 6;
    }

    h = this._hue === null ? h : this._hue;

    return [h, s, v];
};

remix.Color.prototype.set_rgb = function (rgb) {
    this.rgba[0] = rgb[0];
    this.rgba[1] = rgb[1];
    this.rgba[2] = rgb[2];
    this._hue = null;
};

remix.Color.prototype.set_hsv = function (hsv) {
    this.set_rgb(remix.Color.hsv_to_rgb(hsv));
    this._hue = hsv[0];
};

remix.Color.prototype.set_alpha = function (alpha) {
    this.rgba[3] = alpha;
};

remix.Color.prototype.get_rgba8 = function () {
    // usages of this will be removed once we cut over to the new remix editor and refactor the tools. --alex
    return this.rgba.slice();
};

