graph_actions = {};

graph_actions.remixed = function (url) {
    var params = {post: url};
    var type = "remix";
    if (current.enable_timeline) {
        FB.api('/me/' + current.fb_namespace + ':' + type , 'post', params,
            function (response) {
                if(response.error){
                    console.log(response.error.message);
                }
            }
        );
    }
};

graph_actions.stickered = function (url) {
    var params = {post: url};
    var type = "sticker";
    if (current.enable_timeline) {
        FB.api('/me/' + current.fb_namespace + ':' + type , 'post', params,
            function (response) {
                if(response.error){
                    console.log(response.error.message);
                }
            }
        );
    }
};
