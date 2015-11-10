var realtime = {};

realtime.subs = {};
realtime.subscribe = function(sync, fun) {
    if (!realtime.subs[sync.channel]) {
        realtime.subs[sync.channel] = new realtime.Channel(sync);
    }
    return realtime.subs[sync.channel].addCallback(fun);
};

realtime.unsubscribe = function(channel_id, uid) {
    var subs = realtime.subs[channel_id];
    if (!subs) {
        return;
    }

    subs.removeCallback(uid);

    if ($.isEmptyObject(subs.callbacks)) {
        delete realtime.subs[channel_id];
    }
};

realtime.Channel = function(sync) {
    this.id = sync.channel;
    this.last_message_id = +sync.last_message_id;
    this.callbacks = {};
};

realtime.Channel._uid = 0;
realtime.Channel._gen_uid = function() {
    return ++realtime.Channel._uid;
};

realtime.Channel.prototype.addCallback = function(fun) {
    var uid = realtime.Channel._gen_uid();
    this.callbacks[uid] = fun;
    return uid;
};

realtime.Channel.prototype.removeCallback = function(uid) {
    delete this.callbacks[uid];
};

realtime.Channel.prototype.updateLastMessageId = function (messages) {
    var self = this;
    /* Deduplicate messages here. Handle message timeouts here.*/
    $.each(messages, function(n, msg) {
        self.last_message_id = Math.max(self.last_message_id, msg.id);
    });
};

realtime.Channel.prototype.onMessages = function(messages) {
    var payloads = $.map(messages, function(message) { return message.payload; });
    $.each(this.callbacks, function(uid, fun) {
        try {
            fun(payloads);
        } catch (exc) {
            console.log(exc);
        }
    })
};

realtime.backoff = 1;

realtime._backoffCycle = function() {
    var t = realtime.backoff * realtime.backoff;
    realtime.backoff += 1;
    console.log('backing off', t, arguments);
    realtime._query_later(t*1000);
};

realtime._continue = function () {
    realtime.backoff = 1;
    realtime._query_later(200);
}

realtime.ResultHandler = Object.createSubclass();

realtime.ResultHandler.prototype.init = function () {
    this._aborted = false;
};

realtime.ResultHandler.prototype.abort = function () {
    this._aborted = true;
};

realtime.ResultHandler.prototype.on_error = function (result, textStatus) {
    if (this._aborted) return;
    realtime._backoffCycle.apply(this, arguments);
};

realtime.ResultHandler.prototype.on_success = function (result) {
    if (this._aborted) return;

    try {
        if (result.success) {
            delete result.success;
            $.each(result, function(channel_id, messages) {
                realtime.update_lmid(channel_id, messages);
                if (realtime._paused) {
                    realtime._paused_queue.push([channel_id, messages])
                } else {
                    realtime.dispatch_messages(channel_id, messages);
                }
            })
        } else {
            throw result.reason;
        }

        realtime._continue();
    } catch (err) {
        realtime._backoffCycle('realtime._query err', err);
    }
};

realtime._query = function() {
    var channel_ids = [],
        message_ids = [];

    $.each(realtime.subs, function(_, channel) {
        channel_ids.push(channel.id);
        message_ids.push(channel.last_message_id);
    });

    // Generate a random subdomain rt_0 - rt_3.
    var random_sub = "rt_" + Math.floor(Math.random()*4);
    // Create the rt endpoint based on the random letter and the current domain.
    var endpoint = window.location.protocol + '//' + random_sub + "." + window.location.host + '/rt';

    var handler = realtime._handler = new realtime.ResultHandler();

    realtime._connection = $.ajax({
        type: "GET",
        url: endpoint,
        dataType: "jsonp",
        traditional: true,
        timeout: 60000,
        data: {
            c: channel_ids,
            m: message_ids,
            cache_break: Math.random(),
        },
        error: $.proxy(handler.on_error, handler),
        success: $.proxy(handler.on_success, handler),
    });
};

realtime.start = function() {
    realtime._started = true;
    realtime._query_later(2000);
};

realtime._query_later = function (t) {
    realtime._timeout_id = setTimeout(realtime._query, t);
};

realtime.refresh = function () {
    if (!realtime._started) {
        return;
    }

    if (realtime._timeout_id) {
        clearTimeout(realtime._timeout_id);
        delete realtime._timeout_id;
    }

    if (realtime._handler) {
        realtime._handler.abort();
        delete realtime._handler;
    }

    realtime._continue();
}

realtime.update_lmid = function(channel_id, messages) {
    var channel = realtime.subs[channel_id];
    if (channel) {
        channel.updateLastMessageId(messages);
    }
};

realtime.dispatch_messages = function(channel_id, messages) {
    var channel = realtime.subs[channel_id];
    if (channel) {
        channel.onMessages(messages);
    }
};

realtime._paused = 0;
realtime._paused_queue = [];
realtime.pause_updates = function() {
    console.log('realtime.pause_updates');
    realtime._paused++;
};

realtime.unpause_updates = function() {
    realtime._paused = Math.max(0, realtime._paused - 1);
    console.log('realtime.unpause_updates');
    if (realtime._paused == 0 && realtime._paused_queue.length) {
        console.log('realtime.unpause_updates', 'replaying');
        $.each(realtime._paused_queue, function (i, args) {
            realtime.dispatch_messages.apply(null, args);
        });
        realtime._paused_queue = [];
    }
};

realtime.subscribe_channels = function() {
    // User Channel (stickers, inventory, notifications)
    if (current.user_channel) {
        realtime.subscribe(current.user_channel, function (messages) {
            $.each(messages, function (i, message) {
                if (message.msg_type == "sticker_recv") {
                    current.sticker = message.sticker;
                    header.sticker_receieved();
                } else if (message.msg_type == "inventory_changed") {
                    stickers.update_counts(message.counts);
                }
            });
        });
    }

    // Flagged mod channel
    if (current.flag_channel) {
        realtime.subscribe(current.flag_channel, function (messages) {
            $.each(messages, function (i, message) {
                current.flagged = message.flagged;
            });
            header.update_flagged_count();
        });
    }
};

