module("test_stickers");

test_stickers = {};

test_stickers.mock_fun = function () {
    var fun = function () {
        fun.call_count += 1;
    }

    fun.call_count = 0;

    return fun;
}

test_stickers.mock_sticker_effects = function (fun) {
    var old_effects = stickers.effects;

    stickers.effects = {};
    $.each(old_effects, function (name, value) {
        if (typeof value == "function") {
            stickers.effects[name] = test_stickers.mock_fun();
        }
    });

    try {
        fun();
    } finally {
        stickers.effects = old_effects;
    }
}
