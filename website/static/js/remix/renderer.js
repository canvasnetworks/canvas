
remix.Renderer = function (composite, foreground, background) {
    this.composite = composite;
    this.foreground = foreground;
    this.background = background;
    this.reset();
};

remix.Renderer.prototype.reset = function (metadata) {
    this.temp = $('<canvas>');
    this.render_method = "normal";
    this.width = this.height = 0;
    this.history = new remix.History(this);

    var metadata_defaults = {
        used_stamps: [],
        used_text: "",
    };

    this.metadata = $.extend(true, metadata_defaults, metadata);

    this._fact_timers = {};
}

remix.Renderer.prototype.temp_canvas = function (width, height) {
    if (width === undefined) { width = this.width; }
    if (height === undefined) { height = this.height; }
    return $('<canvas>').attr({width: width, height: height});
};

remix.Renderer.prototype.resize = function (width, height) {
    $.each(this.get_all_canvases(), function (i, element) {
        remix._resize(element, {width: width, height: height});
    });
    this.width = width;
    this.height = height;
};

remix.Renderer.prototype.choose_method = function (method) {
    this.render_method = method;
    this.render(false);
};

remix.Renderer.prototype.size = function () {
    return { width: this.composite.width(), height: this.composite.height() };
}

remix.Renderer.prototype.render = function (checkpoint, hide_ui) {
    if (this.current_tool) {
        var fg_ctx = this.foreground.ctx();
        this._buffer = remix.save_canvas(fg_ctx);
        fg_ctx.save();
        this.current_tool.render(fg_ctx);
        fg_ctx.restore();
    }

    if (this.render_method == "normal") {
        this._old_render();
    } else if (remix.blend_modes[this.render_method]) {
        this._new_render(remix.blend_modes[this.render_method]);
    }

    if (checkpoint) {
        this.history.checkpoint();
        delete this._buffer;
    }

    if (this.current_tool && this.current_tool.draw_ui && !hide_ui) {
        this.current_tool.draw_ui();
    }

    if (this._buffer) {
        remix.restore_canvas(this._buffer, this.foreground.ctx());
        delete this._buffer;
    }

    if (this.current_tool && checkpoint && this.history.past.length) {
        this._record_tool_usage(this.current_tool);
    }
};

remix.Renderer.prototype.use_tool = function (tool) {
    this.finish_current_tool();
    this.current_tool = tool;
    this.history.update_display();
}

remix.Renderer.prototype._record_tool_usage = function (tool) {
    var name = tool.tool_name;
    var now = canvas.unixtime();
    if (this._fact_timers[name] && now < this._fact_timers[name] + 5) {
        return;
    }
    this._fact_timers[name] = now;
    canvas.record_metric('remix_tool_used', {'tool': name});
    if (window.current && window.current.share_page) {
        canvas.record_fact('flow_remix_tool_used', {'tool': name});
    }
};

remix.Renderer.prototype._old_render = function () {
    var layers = [this.background.ctx(), this.foreground.ctx()];
    var ctx = this.composite.ctx();

    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    for (var i = 0; i < layers.length; i++) {
        var ele = layers[i].canvas;
        ctx.drawImage(ele, 0,0);
    }

    if (this.current_tool) {
        this.current_tool.preview();
    }
};

remix.Renderer.prototype._new_render = function (blend_fun) {
    // draw fg into composite, then preview, then use that as foreground for blend.
    // TODO: Make this make sense
    var ctx = this.composite.ctx();
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    var fgc = this.foreground.get(0);
    ctx.drawImage(this.foreground.get(0), 0,0);

    if (this.current_tool) {
        this.current_tool.preview();
    }

    // Calculate the blended FG result
    var output = ctx.createImageData(ctx.canvas.width, ctx.canvas.height);
    blend_fun(
        this.background.ctx().getImageData(0,0, ctx.canvas.width, ctx.canvas.height).data,
        ctx.getImageData(0,0, ctx.canvas.width, ctx.canvas.height).data,
        output.data
    );

    // putImageData, then render to correctly get Alpha.
    var temp = this.temp.ctx();
    var bgc = this.background.get(0);
    remix.clear(temp);
    temp.putImageData(output, 0,0);

    // Actually render
    ctx.clearRect(0,0, ctx.canvas.width, ctx.canvas.height);
    ctx.drawImage(bgc, 0,0);
    ctx.drawImage(temp.canvas, 0,0);
};

remix.Renderer.prototype.get_all_canvases = function () {
    return [this.composite, this.foreground, this.background, this.temp];
};

remix.Renderer.prototype.get_fliprotate_contexts = function () {
    return [this.foreground.ctx(), this.background.ctx(), this.temp.ctx()];
};

remix.Renderer.prototype.get_layer_contexts = function () {
    // Returns contexts in visual order, starting at the bottom (back)
    return [this.background.ctx(), this.foreground.ctx()];
};

remix.Renderer.prototype.finish_current_tool = function (done) {
    if (this.current_tool) {
        this.current_tool.finalize(remix.state.last, done)
    }
};

remix.Snapshot = function (renderer) {
    this.renderer = renderer;

    var contexts = this.renderer.get_layer_contexts();

    var ele = contexts[0].canvas;

    this.width = ele.width;
    this.height = ele.height;
    this.layers = [];

    for (var i = 0; i < contexts.length; i++) {
        this.layers.push(remix.save_canvas(contexts[i]));
    }

    this.metadata = $.extend(true, {}, this.renderer.metadata);
};

remix.Snapshot.prototype.restore = function () {
    this.metadata = $.extend(true, {}, this.metadata);

    var contexts = this.renderer.get_layer_contexts();

    $.each(this.layers, function (i, image_data) {
        remix.restore_canvas(image_data, contexts[i]);
    });

    remix._resize(this.renderer.composite, this);
    this.renderer.render(false);
};

remix.History = function (renderer) {
    this.renderer = renderer;
    this.past = [];
    this.current = null;
    this.future = [];
    this.max_history = 10;
    this.update_display();
};

remix.History.prototype.checkpoint = function () {
    if (this.past.length > this.max_history) {
        this.past.shift();
    }

    if (this.current) {
        this.past.push(this.current);
    }
    this.current = new remix.Snapshot(this.renderer);
    this.future = [];
    this.update_display();
};

remix.History.prototype.update_display = function () {
    var has_future = this.future.length != 0;
    var has_past = this.past.length != 0 || (this.renderer.current_tool && this.renderer.current_tool.update_on_finalize);
    this.renderer.composite.trigger('history_update', [has_past, has_future]);
};

remix.History.prototype.undo = function () {
    // Finalize the current tool first, so you can undo unfinalized text or stamps.
    this.renderer.finish_current_tool(false);
    this.move(this.past, this.future);
};

remix.History.prototype.redo = function () {
    this.move(this.future, this.past);
};

remix.History.prototype.move = function (stack_from, stack_to) {
    if (!stack_from.length) return;
    if (!this.current) return;
    stack_to.push(this.current);
    this.current = stack_from.pop();
    this.current.restore();
    this.update_display();
};

