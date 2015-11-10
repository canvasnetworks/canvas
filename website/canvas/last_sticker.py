from canvas import economy


def get_info(user):
    comment_id = user.kv.last_sticker_comment_id.get()
    if comment_id:
        from canvas.models import Comment
        details = Comment.details_by_id(comment_id)()
        url = details.url
    else:
        url = None
    
    level = user.kv.sticker_level.get()
    schedule = economy.sticker_schedule(level)
    
    return {
        'type_id': user.kv.last_sticker_type_id.get(),
        'timestamp': user.kv.last_sticker_timestamp.get(),
        'comment_id': comment_id,
        'url': url,
        'level': level, 
        'level_progress': user.kv.sticker_inbox.get(),
        'level_total': schedule,            
    }

def set_sticker(user, sticker):
    user.kv.last_sticker_type_id.set(sticker.type_id)
    user.kv.last_sticker_timestamp.set(sticker.timestamp)
    user.kv.last_sticker_comment_id.set(sticker.comment_id)
    
def realtime_update_sticker_receipt(recipient):
    recipient.redis.channel.publish({'msg_type': 'sticker_recv', 'sticker': get_info(recipient)})

