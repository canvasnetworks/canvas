from canvas.details_models import RealtimeCommentDetails

def update_realtime(comment_details):
    realtime_details = RealtimeCommentDetails(comment_details)
    comment_details.updates_channel.publish(realtime_details)

