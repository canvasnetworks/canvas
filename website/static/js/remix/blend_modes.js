
remix.blend_modes = {};

/* Official documentation on PDF's blend modes: http://www.aiim.org/documents/standards/pdf/blend_modes.pdf */

remix.blend_modes.multiply = function (lhs, rhs, output) {
    var length = lhs.length;
    for (var n = 0; n < length; n += 4) {
        output[n]   = lhs[n]   * rhs[n]   / 255;
        output[n+1] = lhs[n+1] * rhs[n+1] / 255;
        output[n+2] = lhs[n+2] * rhs[n+2] / 255;
        output[n+3] = rhs[n+3];
    }
};

remix.blend_modes.darken = function (lhs, rhs, output) {
    var length = lhs.length;
    var min = Math.min;
    for (var n = 0; n < length; n += 4) {
        output[n]   = min(lhs[n]  , rhs[n]  );
        output[n+1] = min(lhs[n+1], rhs[n+1]);
        output[n+2] = min(lhs[n+2], rhs[n+2]);
        output[n+3] = rhs[n+3];
    }
};

remix.blend_modes.lighten = function (lhs, rhs, output) {
    var length = lhs.length;
    var max = Math.max;
    for (var n = 0; n < length; n += 4) {
        output[n]   = max(lhs[n]  , rhs[n]  );
        output[n+1] = max(lhs[n+1], rhs[n+1]);
        output[n+2] = max(lhs[n+2], rhs[n+2]);
        output[n+3] = rhs[n+3];
    }
};

remix.blend_modes.lighter_color = function (lhs, rhs, output) {
    var length = lhs.length;
    for (var n = 0; n < length; n += 4) {
        var pick = (lhs[n] + lhs[n+1] + lhs[n+2] > rhs[n] + rhs[n+1] + rhs[n+2]) ? lhs : rhs;
        output[n]   = pick[n];
        output[n+1] = pick[n+1];
        output[n+2] = pick[n+2];
        output[n+3] = rhs[n+3];
    }
};

remix.blend_modes.darker_color = function (lhs, rhs, output) {
    var length = lhs.length;
    for (var n = 0; n < length; n += 4) {
        var pick = (lhs[n] + lhs[n+1] + lhs[n+2] <= rhs[n] + rhs[n+1] + rhs[n+2]) ? lhs : rhs;
        output[n]   = pick[n];
        output[n+1] = pick[n+1];
        output[n+2] = pick[n+2];
        output[n+3] = rhs[n+3];
    }
};

remix.blend_modes.screen = function (lhs, rhs, output) {
    var length = lhs.length;
    for (var n = 0; n < length; n += 4) {
        output[n]   = 255 - (((255 - lhs[n]  ) * (255 - rhs[n]  )) / 255);
        output[n+1] = 255 - (((255 - lhs[n+1]) * (255 - rhs[n+1])) / 255);
        output[n+2] = 255 - (((255 - lhs[n+2]) * (255 - rhs[n+2])) / 255);
        output[n+3] = rhs[n+3];
    }
};

remix.blend_modes.color_burn = function (lhs, rhs, output) {
    var length = lhs.length;
    for (var n = 0; n < length; n += 4) {
        output[n]   = rhs[n]   != 0 ? 255 - 255 * (255-lhs[n]  ) / rhs[n]   : 0;
        output[n+1] = rhs[n+1] != 0 ? 255 - 255 * (255-lhs[n+1]) / rhs[n+1] : 0;
        output[n+2] = rhs[n+2] != 0 ? 255 - 255 * (255-lhs[n+2]) / rhs[n+2] : 0;
        output[n+3] = rhs[n+3];
    }
};

remix.blend_modes.color_dodge = function (lhs, rhs, output) {
    var length = lhs.length;
    for (var n = 0; n < length; n += 4) {
        output[n]   = rhs[n]   != 255 ? 255*lhs[n]  /(255-rhs[n]  ) : 255;
        output[n+1] = rhs[n+1] != 255 ? 255*lhs[n+1]/(255-rhs[n+1]) : 255;
        output[n+2] = rhs[n+2] != 255 ? 255*lhs[n+2]/(255-rhs[n+2]) : 255;
        output[n+3] = rhs[n+3];
    }
};

remix.blend_modes.difference = function (lhs, rhs, output) {
    var length = lhs.length;
    var abs = Math.abs;
    for (var n = 0; n < length; n += 4) {
        output[n]   = abs(lhs[n]   - rhs[n]  );
        output[n+1] = abs(lhs[n+1] - rhs[n+1]);
        output[n+2] = abs(lhs[n+2] - rhs[n+2]);
        output[n+3] = rhs[n+3];
    }
};

remix.blend_modes.exclusion = function (lhs, rhs, output) {
    var length = lhs.length;
    for (var n = 0; n < length; n += 4) {
        output[n]   = lhs[n]   + rhs[n]   - 512 * (lhs[n]   * rhs[n]   / 65025);
        output[n+1] = lhs[n+1] + rhs[n+1] - 512 * (lhs[n+1] * rhs[n+1] / 65025);
        output[n+2] = lhs[n+2] + rhs[n+2] - 512 * (lhs[n+2] * rhs[n+2] / 65025);
        output[n+3] = rhs[n+3];
    }
};
