var loadingVar = Math.floor(Math.random()*20000);
if (loadingVar == 1) {
    $('<img id="loadingImg" src="/static/img/spinner.gif" style="display:block;position:absolute;z-index:100;left:100px;">').insertAfter("#header nav:not(.clone) .second_tier");
    setTimeout('$("#loadingImg").remove()', 4000);
}
$('script[src="/static/js/loading.js"]').remove();
