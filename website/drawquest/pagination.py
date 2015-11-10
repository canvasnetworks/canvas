from itertools import dropwhile, takewhile


class Paginator(object):
    def __init__(self, items, per_page, since_id=None, before_id=None):
        """
        `items` must have `id` properties and must be sorted in order of `id`.
        """
        self.per_page = per_page
        self.since_id = since_id
        self.before_id = before_id

        total_count = len(items)

        if since_id is not None:
            items = dropwhile(lambda c: c.id < since_id, items)

        if before_id is not None:
            items = takewhile(lambda c: c.id < before_id, items)

            if since_id is None:
                items = list(items)[-per_page:]
        else:
            items = list(items)[:per_page]

        self.items = items = list(items)

        self.has_more = len(items) != total_count

        try:
            self.min_id = min(item.id for item in items)
        except (IndexError, ValueError,):
            self.min_id = None

        try:
            self.max_id = max(item.id for item in items)
        except (IndexError, ValueError,):
            self.max_id = None

    def to_client(self):
        return {
            'min_id': self.min_id,
            'max_id': self.max_id,
            'more': self.has_more,
        }

