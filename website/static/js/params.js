(function() {
    var re = /([^&=]+)=?([^&]*)/g;
    var decodeRE = /\+/g;  // Regex for replacing addition symbol with a space
    var decode = function (str) {
        return decodeURIComponent(str.replace(decodeRE, " "));
    };
    $.parseParams = function(query) {
        if (query.indexOf('?') != -1) {
            query = query.split('?')[1] || query;
        }
        var params = {};
        var e;
        while (e = re.exec(query)) {
            params[decode(e[1])] = decode(e[2]);
        }
        return params;
    };
})();

