from canvas.shortcuts import r2r_jinja

def submit_quest_wrapper(request):
    return r2r_jinja('submit_quest/submit_quest_wrapper.html', {}, request)

def submit_quest(request):
    ctx = {}
    return r2r_jinja('submit_quest/submit_quest_iframe.html', ctx, request)

def success(request):
    return r2r_jinja('submit_quest/success.html', {}, request)

