canvas.upload_endpoint = "/api/upload"; // "/ugc" for old style

canvas.uploadify = function (root, listener) {
    // If we double wire uploadify, then our onSuccess handler gets called twice.
    // This used to require that the upload element be visible, but that check was based on lies and treachery. Probably.
    root = $(root).filter(function (_, el) {
        return (!root.hasClass('wired_for_uploadify'));
    });
    if (!root.length) {
        return;
    }
    root.addClass('wired_for_uploadify');

    // First check that we have flash.
    // Otherwise disable the button.
    if (!swfobject.hasFlashPlayerVersion('9.0.24')) {
        $(root).attr('disabled', true).after('<div class="no_flash">Please install Flash.</div>');
        return;
    }

    var uploader = $('input[type=file]', root);
    var link = $('.uploadify_link', root);
    root.css('position', 'relative');
    uploader.css('display', 'none');

    // Generate a random ID for the input so uploadify is happy.
    uploadify_input = $('.uploadify_input', root);
    uploadify_input.attr('id', 'uploadify_input_'+canvas.getUID());

    uploader.uploadify({
        uploader: '/static/lib/uploadify/uploadify.swf',
        script: canvas.upload_endpoint + '?is_quest=1',
        multi: false,
        fileDataName: 'file',
        fileExt: '*.jpeg;*.jpg;*.png;*.gif;*.bmp',
        fileDesc: 'Image',
        cancelImg: '/static/lib/uploadify/cancel.png',
        /*buttonImg: '/static/img/upload-image.png',*/
        wmode: 'transparent',
        hideButton: true,
        width: link.outerWidth(),
        height: link.outerHeight(),
        auto: true,
        scriptData: {
            sessionid: getCookie('sessionid'),
            csrfmiddlewaretoken: getCookie('csrftoken'),
        },
        onSelect: function (event, queueID, fileObj) {
            fileObj['mode'] = 'upload';
            canvas.track_upload_attempt('uploadify', {size: fileObj.size, name: fileObj.name});
            $(listener).trigger('uploadstart', fileObj);
            console.log('uploadstart');
            return false;
        },
        onProgress: function (event, queueId, fileObj, data) {
            $(listener).trigger('uploadprogress', data);
        },
        onComplete: function (e,q,f,response,d) {
            var blob = JSON.parse(response);
            canvas._handle_results('uploadify', listener, blob);
        },
        onError: function (e, q, f, o) {
            $(listener).trigger('uploadfail', "Uploadify:" + o.type.toString() + ": " + o.info);
        },
        onSWFReady: function () {
            $('object', root).css('position', 'absolute');
        },
        folder: '/uploads',
    });
};

canvas._handle_results = function (upload_type, listener, response) {
    if (response['success']) {
        var content = canvas.storeContent(response.content);
        canvas.record_metric('upload_success', {upload_type: upload_type});
        $(listener).trigger('uploadend', [content, response, upload_type]);
        return content;
    } else {
        canvas.record_metric('upload_fail', {upload_type: upload_type});
        $(listener).trigger('uploadfail', response['reason']);
        throw new Error(response['reason']);
    }
};

canvas._handle_failure = function (upload_type, listener, response) {
    $(listener).trigger('uploadfail', response.statusText);
    canvas.record_metric('upload_network_fail', {upload_type: upload_type});
    throw new Error(response.statusText);
};

canvas.upload_url = function (url, listener) {
    $(listener).trigger('uploadstart', {'mode': 'transfer'});

    var content_id = canvas.parse_curi(url);
    if (content_id) {
        var content = canvas.getContent(content_id);
        $(listener).trigger('uploadend', content);
    } else {
        canvas.track_upload_attempt('url', {'upload_url': url});
        return canvas.jsonPOST(
            canvas.upload_endpoint + '?is_quest=1',
            { url: url},
            null,
            15 * 1000 // timeout in milliseconds
        ).then(
            canvas._handle_results.partial('url', listener),
            canvas._handle_failure.partial('url', listener)
        );
    }
};

canvas.upload_canvas = function (c, listener, metadata) {
    $(listener).trigger('uploadstart', {'mode': 'transfer'});
    var png_data = $(c).get(0).toDataURL('image/png');
    canvas.track_upload_attempt('remix', {'bytes': png_data.length});
    return $.ajax({
        url: canvas.upload_endpoint + '?' + $.param(metadata),
        type: 'POST',
        contentType: 'application/base64-png',
        data: png_data,
        timeout: 60 * 1000 // timeout in milliseconds. Note that this does not depend on the user's connection speed.
    })
    .done(canvas._handle_results.partial('remix', listener))
    .fail(canvas._handle_failure.partial('remix', listener));
};

canvas.upload_canvas_chunked = function (c, listener, metadata, is_quest) {
    $(listener).trigger('uploadstart', {'mode': 'transfer'});
    var data = $(c).get(0).toDataURL("image/png").slice("data:image/png;base64,".length);

    canvas.track_upload_attempt('remix', {'bytes': data.length});

    var slice_length = 50 * 1024;

    function fail () {
        canvas._handle_failure('remix', listener)
    }

    var all_chunks = [];
    var total_chunks = Math.ceil(data.length / slice_length);
    for (var i = 0; i < total_chunks; ++i) {
        all_chunks.push(i);
    }

    var chunks_sent = 0;
    function incr_progress() {
        chunks_sent += 1;
        var percentage = Math.floor(chunks_sent / all_chunks.length * 100);
        $(listener).trigger('uploadprogress', {percentage:  percentage})

    }

    function send_chunk(i) {
        var start = i * slice_length;
        var chunk = data.slice(start, start + slice_length);

        var d = $.Deferred();

        function attempt_upload(remaining, last_error) {
            if (remaining <= 0) {
                d.rejectWith(null, [last_error]);
            } else {
                canvas.api.upload_chunk(chunk)
                    .done(function (result) {
                        incr_progress();
                        d.resolveWith(null, [result]);
                    })
                    .fail(function (error) {
                        console.log('error', error, 'retrying', remaining-1, 'times')
                        attempt_upload(remaining - 1, error);
                    });
            }
        }

        attempt_upload(3);

        return d.promise();
    }

    function send_chunks(chunks) {
        var d = $.Deferred();
        var chunk_names = [];

        var send_more = function (result) {
            if (chunks.length) {
                send_chunk(chunks.shift())
                    .fail(function (error) {
                        d.rejectWith(null, [error]);
                    })
                    .done(function (result) {
                        chunk_names.push(result.chunk_name);
                        send_more();
                    });
            } else {
                d.resolveWith(null, [chunk_names]);
            }
        };

        send_more();

        return d;
    }

    function send_file(chunks, parallelism) {
        var d = $.Deferred();
        var deferreds = [];
        var chunks_per_thread = Math.ceil(chunks.length / parallelism);

        console.log('cpt', chunks_per_thread);

        for (var i = 0; i < parallelism; ++i) {
            var thread_chunks = chunks.slice(i*chunks_per_thread, (i+1)*chunks_per_thread);
            deferreds.push(send_chunks(thread_chunks));
        }

        $.when.apply($, deferreds)
            .done(function () {
                d.resolveWith(null, [Array.prototype.concat.apply([], arguments)]);
            })
            .fail(function (reason) {
                d.rejectWith(null, [reason]);
            });

        return d;
    }

    send_file(all_chunks, 4).fail(fail).done(function (chunks) {
        console.log('uploading', chunks);
        canvas.api.combine_upload_chunks(chunks, metadata, is_quest)
            .done(canvas._handle_results.partial('remix', listener))
            .fail(fail);
    });
};

canvas.track_upload_attempt = function (upload_type, meta) {
    canvas.record_metric('upload_attempt', $.extend(meta, {upload_type: upload_type}));
};
