var mutex = {};

mutex.show = function (all, specifier) {
    // Example: mutex.show(".frontpage", ".login")
    var base = ".mutex" + all;
    $(base).removeClass("mutex-shown");
    $(base + specifier).addClass("mutex-shown");
}
