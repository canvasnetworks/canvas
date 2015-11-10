
remix.Text = remix.Stampable.createSubclass();

remix.Text.prototype.init = function () {
    remix.Text.__super__.init.apply(this, arguments);
    this.tool_name = "text";
    this.place();
};
remix.Text.tool_name = 'text';

remix.Text.prototype.record_metadata = function() {
    this.renderer.metadata.used_text += this.get_params().text + "\n";
};

remix.Text.prototype.modes['new'].place = function () {
    var w = this.renderer.composite.width();

    var rect = new remix.Rect({ x: 0, y: 0 }, {
        width: w - 30,
        height: 36, //TODO
    });

    this.center({x: w/2, y: 30}, rect);
    this.rot = 0;
    this.mode = 'placing'; // Instant switch before render
    this.update_on_finalize = true;

    this.renderer.render();
};

remix.Text.prototype.word_wrap = function (ctx, text, max_width) {
    // Handles both word and character wrapping (for individual words that are too wide.)
    // Adapted from http://mudcu.be/journal/2011/01/html5-typographic-metrics/
    var returns = text.split('\n');
    var lines = [];
    var last_phrase = '';

    function split_word() {
        // Returns list of lines, or nothing if the word already fits.
        var width = ctx.measureText(last_phrase).width;
        var char_lines = [];
        var line = '';
        if (width > max_width) {
            for (var n = 0, length = last_phrase.length; n < length; n++) {
                var c = last_phrase.substr(n, 1);
                var width = ctx.measureText(line + c).width;
                if (width <= max_width) {
                    line += c;
                } else {
                    if (line) {
                        char_lines.push(line);
                        line = c;
                    } else {
                        char_lines.push(c);
                        line = '';
                    }
                }
            }
            if (last_phrase.length > 1) {
                char_lines.push(line);
            }
            return char_lines;
        }
    };

    for (var n = 0; n < returns.length; n++) {
        if (last_phrase) {
            lines.push(last_phrase);
        }
        var phrase = returns[n];
        var words = phrase.split(" ");
        var last_phrase = "";
        for (var i = 0; i < words.length; i++) {
            var current_phrase = words[i];
            if (last_phrase) {
                current_phrase = last_phrase + ' ' + current_phrase;
            }
            var measure = ctx.measureText(current_phrase).width;
            if (measure <= max_width) {
                last_phrase += ((last_phrase ? ' ' : '') + words[i]);
            } else {
                var split = split_word();
                if (split && split.length) {
                    for (var j = 0; j < split.length - 1; j++) {
                        lines.push(split[j]);
                    }
                    last_phrase = split[split.length - 1] + " " + words[i];
                } else {
                    if (last_phrase) {
                        lines.push(last_phrase);
                    }
                    last_phrase = words[i];
                }
            }
            if (i == words.length - 1) {
                var split = split_word();
                if (split) {
                    lines = lines.concat(split);
                } else {
                    lines.push(last_phrase);
                }
                break;
            }
        }
    }
    return lines;
};

remix.Text.prototype.text_height = function (ctx, text, font_family, font_size) {
    // An awful hack adapted from http://mudcu.be/journal/2011/01/html5-typographic-metrics/
    var control = document.createElement('span');
    var img = document.createElement('img');
    control.style.display = 'none';
    control.style.position = 'fixed';
    control.style.top = 0;
    control.style.left = '-9999999px';
    control.style.fontSize = font_size;
    control.style.fontFamily = font_family;
    document.body.appendChild(control);
    img.width = 42;
    img.height = 1;
    img.src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQMAAAAl21bKAAAAA1BMVEUAAACnej3aAAAAAXRSTlMAQObYZgAAAApJREFUCNdjYAAAAAIAAeIhvDMAAAAASUVORK5CYII%3D'; // 1x1 png
    text_node = document.createTextNode(text)
    text_node.width = '9999999px';
    control.appendChild(text_node);
    control.appendChild(img);
    img.style.display = 'none';
    control.style.display = 'inline';
    control.textContent = text;
    var height = control.offsetHeight;
    document.body.removeChild(control);
    return height;
};

remix.Text.prototype.draw = function(ctx) {
    var params = this.get_params();

    ctx.save();
    this.rotate(ctx);
    ctx.globalAlpha = params.alpha / 255.0;

    var font_size = params.font_size + "px";
    var font = font_size + " " + params.font_name;
    var text_height = this.text_height(ctx, params.text || 'M', params.font_name, font_size); // defaults to one line tall.

    var padding = text_height / 6;

    ctx.font = font;
    ctx.fillStyle = params.text_inner_color.get_css();
    ctx.textAlign = params.text_alignment;
    ctx.textBaseline = 'bottom';

    var lines = this.word_wrap(ctx, params.text, this.rect.width - (padding * 2));

    var new_height = Math.ceil(text_height * lines.length + (padding * 2));

    if (this.rot == 0) {
        // Push the text down if it's not rotated
        this.rect.height = new_height;
    } else {
        // Otherwise the text grows from the center
        this.rect = remix.Rect.centeredRect(this.rect.center(), {width: this.rect.width, height: new_height});
    }

    var y = this.rect.y + padding + text_height;
    if(params.text_alignment === 'center') {
        var x = this.rect.x + (this.rect.width / 2);
    } else if (params.text_alignment === 'left') {
        var x = this.rect.x + padding;
    } else if (params.text_alignment === 'right') {
        var x = this.rect.x + this.rect.width - padding;
    }

    for (var i = 0; i < lines.length; i++) {
        line = lines[i];
        ctx.fillText(line, x, y);
        if (params.text_has_outline) {
            ctx.strokeStyle = params.text_outline_color.get_css();

            var fsize = params.font_size;
            var factor = 4.0;

            ctx.lineWidth = (factor * fsize / 128.0);
            ctx.strokeText(line, x,y);
        }
        y += text_height;
    };

    ctx.restore();
};

remix.Text.prototype.pick_points = ['cl', 'cr'];

