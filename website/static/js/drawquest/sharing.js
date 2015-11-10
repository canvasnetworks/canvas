window.share = function(share_type, quest_title, img_url) {
    var url = window.document.location.href;
    if (share_type == "facebook") {
        obj = {
            method  : 'feed',
            redirect_uri    : url,
            link            : url,
            picture         : img_url,
            name            : quest_title,
            caption         : "DrawQuest is a free drawing community exclusively for iPad. Every day, people come together on DrawQuest to draw the Quest of the Day."
        };
        FB.ui(obj);
    } else if (share_type == "twitter") {
        var message = quest_title + " " + url + " via @DrawQuest";
        window.open('http://twitter.com/intent/tweet?text=' + encodeURIComponent(message), "twitter_share", "width=600, height=400");
    } else if (share_type == "tumblr") {
        var message = quest_title + " " + url;
        window.open('http://www.tumblr.com/share/photo?source=' + encodeURIComponent(img_url + "?tumblr") + '&clickthru=' + encodeURIComponent(url) + '&caption=' + encodeURIComponent(message), "tumblr_share", "width=450, height=400");
    }
};
