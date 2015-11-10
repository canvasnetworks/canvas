remix.filters = {};

remix.filters.filtrr_helper = function (fun) {
    return function (renderer) {
        filtrr.canvas(renderer.composite.get(0), function (filtr) {
            fun(filtr);
            renderer.foreground.ctx().putImageData(filtr.getCurrentImageData(), 0,0);
            renderer.render(true);
        });
    };
};

remix.filters.grayscale = remix.filters.filtrr_helper(function (output) {
    output.core.grayScale();
});

remix.filters.noir = remix.filters.filtrr_helper(function (output) {
    output.core.grayScale().tint([60,60,30], [210, 210, 210]);
});

remix.filters.vintage = remix.filters.filtrr_helper(function (output) {
    var topFiltr = output.duplicate();
    topFiltr.core.tint([20, 35, 10], [150, 160, 230]).saturation(0.6);
    output.core.adjust(0.1,0.7,0.4).saturation(0.6).contrast(0.8);
    output.blend.multiply(topFiltr);
});

remix.filters.imagefilter_helper = function (fun) {
    return function (renderer) {
        var size = renderer.size();
        var pixel_data = renderer.composite.ctx().getImageData(0,0, size.width, size.height);
        renderer.foreground.ctx().putImageData(fun(pixel_data), 0,0);
        renderer.render(true);
    };
};

remix.filters.jsmanipulate_helper = function (fun) {
    return function (renderer) {
        var size = renderer.size();
        var pixel_data = renderer.composite.ctx().getImageData(0,0, size.width, size.height);
        fun(pixel_data);
        renderer.foreground.ctx().putImageData(pixel_data, 0,0);
        renderer.render(true);
    };
};

remix.filters.mosaic = remix.filters.imagefilter_helper(function (pixel_data) {
    return ImageFilters.Mosaic(pixel_data, 8);
});

remix.filters.eight_bit = remix.filters.imagefilter_helper(function (pixel_data) {
    pixel_data = ImageFilters.Mosaic(pixel_data, 8);
    pixel_data = ImageFilters.Posterize(pixel_data, 8);
    return pixel_data;
});

remix.filters.posterize = remix.filters.imagefilter_helper(function (pixel_data) {
    return ImageFilters.Posterize(pixel_data, 8);
});

remix.filters.solarize = remix.filters.imagefilter_helper(function (pixel_data) {
    return ImageFilters.Solarize(pixel_data);
});

remix.filters.oil = remix.filters.imagefilter_helper(function (pixel_data) {
    return ImageFilters.Oil(pixel_data, 3, 32)
});

remix.filters.dither = remix.filters.jsmanipulate_helper(function (pixel_data) {
    return new DitherFilter().filter(pixel_data, {levels: 3});
});

remix.filters.jpeg = function (renderer) {
    var quality = 4;

    var size = renderer.size();
    var pixel_data = renderer.composite.ctx().getImageData(0,0, size.width, size.height);

    var encoder = new JPEGEncoder(quality);
    var output = encoder.encode(pixel_data, quality);

    var img = new Image;
    img.onload = function () {
        renderer.foreground.ctx().drawImage(img, 0,0);
        renderer.render(true);
    };
    img.src = output;
};

remix.filters.gaussian_blur = function (renderer) {
    // from https://github.com/mezzoblue/PaintbrushJS/blob/master/common.js
    // adapted from http://pvnick.blogspot.com/2010/01/im-currently-porting-image-segmentation.html
    function gaussian_blur(pixels, width, height, amount) {
        var width4 = width << 2;

        if (pixels) {
            var data = pixels.data;

            // compute coefficients as a function of amount
            var q;
            if (amount < 0.0) {
                amount = 0.0;
            }
            if (amount >= 2.5) {
                q = 0.98711 * amount - 0.96330; 
            } else if (amount >= 0.5) {
                q = 3.97156 - 4.14554 * Math.sqrt(1.0 - 0.26891 * amount);
            } else {
                q = 2 * amount * (3.97156 - 4.14554 * Math.sqrt(1.0 - 0.26891 * 0.5));
            }

            //compute b0, b1, b2, and b3
            var qq = q * q;
            var qqq = qq * q;
            var b0 = 1.57825 + (2.44413 * q) + (1.4281 * qq ) + (0.422205 * qqq);
            var b1 = ((2.44413 * q) + (2.85619 * qq) + (1.26661 * qqq)) / b0;
            var b2 = (-((1.4281 * qq) + (1.26661 * qqq))) / b0;
            var b3 = (0.422205 * qqq) / b0; 
            var bigB = 1.0 - (b1 + b2 + b3); 

            // horizontal
            for (var c = 0; c < 3; c++) {
                for (var y = 0; y < height; y++) {
                    // forward 
                    var index = y * width4 + c;
                    var indexLast = y * width4 + ((width - 1) << 2) + c;
                    var pixel = data[index];
                    var ppixel = pixel;
                    var pppixel = ppixel;
                    var ppppixel = pppixel;
                    for (; index <= indexLast; index += 4) {
                        pixel = bigB * data[index] + b1 * ppixel + b2 * pppixel + b3 * ppppixel;
                        data[index] = pixel; 
                        ppppixel = pppixel;
                        pppixel = ppixel;
                        ppixel = pixel;
                    }
                    // backward
                    index = y * width4 + ((width - 1) << 2) + c;
                    indexLast = y * width4 + c;
                    pixel = data[index];
                    ppixel = pixel;
                    pppixel = ppixel;
                    ppppixel = pppixel;
                    for (; index >= indexLast; index -= 4) {
                        pixel = bigB * data[index] + b1 * ppixel + b2 * pppixel + b3 * ppppixel;
                        data[index] = pixel;
                        ppppixel = pppixel;
                        pppixel = ppixel;
                        ppixel = pixel;
                    }
                }
            }

            // vertical
            for (var c = 0; c < 3; c++) {
                for (var x = 0; x < width; x++) {
                    // forward 
                    var index = (x << 2) + c;
                    var indexLast = (height - 1) * width4 + (x << 2) + c;
                    var pixel = data[index];
                    var ppixel = pixel;
                    var pppixel = ppixel;
                    var ppppixel = pppixel;
                    for (; index <= indexLast; index += width4) {
                        pixel = bigB * data[index] + b1 * ppixel + b2 * pppixel + b3 * ppppixel;
                        data[index] = pixel;
                        ppppixel = pppixel;
                        pppixel = ppixel;
                        ppixel = pixel;
                    } 
                    // backward
                    index = (height - 1) * width4 + (x << 2) + c;
                    indexLast = (x << 2) + c;
                    pixel = data[index];
                    ppixel = pixel;
                    pppixel = ppixel;
                    ppppixel = pppixel;
                    for (; index >= indexLast; index -= width4) {
                        pixel = bigB * data[index] + b1 * ppixel + b2 * pppixel + b3 * ppppixel;
                        data[index] = pixel;
                        ppppixel = pppixel;
                        pppixel = ppixel;
                        ppixel = pixel;
                    }
                }
            } 

            return(pixels);
        }
    }

    var size = renderer.size();
    var pixel_data = renderer.composite.ctx().getImageData(0,0, size.width, size.height);
    var output = gaussian_blur(pixel_data, size.width, size.height, 6);
    renderer.foreground.ctx().putImageData(output, 0,0);
    renderer.render(true);
};

