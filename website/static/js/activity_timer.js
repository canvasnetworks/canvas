var ActivityTimer = Object.createSubclass();

ActivityTimer.prototype.init = function (selector, timeout) {
    this._base = selector;
    this._accumulated_time = 0;
    this._last_idle = this._last_active = canvas.unixtime();

    var self = this;
    this._base
        .bind('idle.idleTimer', function () {
            self._last_idle = canvas.unixtime();
            self._accumulated_time += self._last_idle - self._last_active;
        })
        .bind('active.idleTimer', function() {
            self._last_active = canvas.unixtime();
        });

    this._base.idleTimer(timeout);
};

ActivityTimer.prototype.get_time = function () {
    var current_activity = 0;
    if (this._base.data('idleTimer') == 'active') {
        current_activity = canvas.unixtime() - this._last_idle;
    }
    return this._accumulated_time + current_activity;
};

ActivityTimer.prototype.stop = function () {
    var active_time = this.get_time();
    this._base.idleTimer('destroy');
    return active_time;
};

