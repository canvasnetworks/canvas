
from canvas import stickers, knobs

def eligible_for_daily_free_stickers(user):
    return (user.is_authenticated()
            and user.kv.daily_free_timestamp.get(nocache=True) <= time.time() - 23 * 60 * 60)

def grant_daily_free_stickers(user, force=False, count=knobs.DAILY_FREE_STICKERS):
    from canvas.notifications.actions import Actions

    if not user.is_authenticated():
        return

    if not force and not eligible_for_daily_free_stickers(user):
        return

    user.kv.daily_free_timestamp.set(time.time())
    user.kv.has_unseen_daily_free_stickers.set(True)

    user.kv.stickers.currency.increment(count)
    Actions.daily_free_stickers(user, count)

def realtime_update_sticker_counts(user):
    counts = dict((sticker.type_id, user.kv.stickers[sticker.type_id].get())
                  for sticker in stickers.get_limited_stickers())
    counts = dict((type_id, count)
                  for (type_id, count) in counts.items()
                  if count)
    user.redis.channel.publish({'msg_type': 'inventory_changed', 'counts': counts})

def level_up(user, only_once=True):
    from canvas.notifications.actions import Actions
    from canvas import last_sticker
    
    reward_stickers = 0

    while user.kv.sticker_inbox.get() >= sticker_schedule(user.kv.sticker_level.get()):
        sticker_level = user.kv.sticker_level.get()
        result = user.kv.sticker_inbox.increment_ifsufficient(-sticker_schedule(sticker_level))

        # If there weren't actually enough, the user was already rewarded in a different request. Update their
        # sticker data.
        if not result['success']:
            user_kv = user.redis.user_kv.hgetall()
            break

        user.kv.sticker_level.increment()
        reward = sticker_schedule(user.kv.sticker_level.get(), reward=True)
        user.kv.stickers.currency.increment(reward)
        reward_stickers += reward
        user_kv = user.redis.user_kv.hgetall()

        Actions.leveled_up(user, reward)
        
        if only_once:
            break
            
    if reward_stickers:
        realtime_update_sticker_counts(user)
        last_sticker.realtime_update_sticker_receipt(user)

    return reward_stickers

def sticker_schedule(level, reward=False):
    if not level:
        level = 0
    idx = level if level < len(knobs.STICKER_SCHEDULE) else -1
    if reward:
        return knobs.STICKER_REWARDS[idx]
    else:
        return knobs.STICKER_SCHEDULE[idx]

class BusinessError(Exception):
    pass

class InvalidInventoryState(BusinessError):
    pass
    
class InvalidPurchase(BusinessError):
    pass

def purchase_stickers(user, type_id, quantity):
    """
    Execute the actual purchase.

    type_id: A Sticker or a sticker type id.
    """
    sticker = stickers.details_for(type_id)
    cost = sticker.cost
    if not cost:
        raise InvalidPurchase('Invalid item_id.')
    cost *= quantity
    
    # Is this a limited inventory sticker?
    if sticker.is_limited_inventory():
        if user.kv.stickers.did_purchase(sticker):
            raise InvalidPurchase("You've already bought this limited availability sticker.")
    
    # Sticker ID of the #1 sticker.    
    result = user.kv.stickers.currency.increment_ifsufficient(-cost)
    #TODO This is nasty, increment_ifsufficient should raise an exception instead of returning status code.
    if result['success']:
        user.kv.stickers.get(type_id).increment(quantity)

    else:
        raise InvalidPurchase('Insufficient balance.')
    
    if sticker.is_limited_inventory:
        user.kv.stickers.mark_sticker_purchased(sticker)
        sticker.decrement_inventory()
        
    realtime_update_sticker_counts(user)
    return result['remaining']

def consume_sticker(user, type_id):    
    result = user.kv.stickers[type_id].increment_ifsufficient(-1)
    if result['success']:
        realtime_update_sticker_counts(user)
        return result['remaining']
    else:
        raise InvalidInventoryState("Out of inventory.")

def credit_received_sticker(user, type_id):
    sticker = stickers.details_for(type_id)

    # Stars get their own handling inside the stars app.
    if not sticker.is_star():
        cost = sticker.cost or 1
        # temp andrew wk stuff
        if type_id == 111:
            cost = 50
        user.kv.stickers_received.increment(cost)
        user.kv.sticker_inbox.increment(cost)

def credit_received_remix(user):
    user.kv.sticker_inbox.increment(knobs.REMIX_POINTS)

