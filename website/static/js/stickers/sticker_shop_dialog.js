canvas.StickerShopDialog = canvas.Dialog.createSubclass();
canvas.StickerShopDialog.panel_speed = 5;

canvas.StickerShopDialog.prototype.default_args = {
    has_alert: false,
    click_to_dismiss: true,
    esc_to_dismiss: true,
};

canvas.StickerShopDialog.prototype.close_panels = function () {
    this.shop.find('.store_item.expanded').each(function (i, item) {
        $(item).removeClass('expanded');
        var desc = $(item).find('.description_panel');
        desc.animate({height: "0px"}, desc.height() * canvas.StickerShopDialog.panel_speed);
    });
};

canvas.StickerShopDialog.prototype.create_content = function () {
    var self = this;
    this.shop = $('.sticker_shop').clone();

    canvas.prevent_scroll_bubbling($('.item_list', this.shop));

    this.shop.find('.done').bind('click', function () {
        self.destroy();
    });

    this.shop.find('.store_item').bind('click', function () {
        var desc = $(this).find('.description_panel');
        var expanded = $(this).hasClass('expanded');
        self.close_panels();
        if (!expanded) {
            desc.css({ height: 'auto' });
            var height = desc.height();
            desc.css({ height: '0px' });
            desc.animate({height: height}, height * canvas.StickerShopDialog.panel_speed);
            $(this).addClass('expanded');
        }
    });

    this.shop.find('.buy').bind('click', function (event) {
        event.stopPropagation();

        var item_id = $(this).data('item-id');
        var item_cost = parseInt($(this).data('item-cost'));
        var sticker_wrapper =  $(this).parents('.store_item').find('.sticker_wrapper');
        var offset = sticker_wrapper.offset();
        var num1_count = self.shop.find('.sticker_currency_count');
        var starting_balance = parseInt(num1_count.text());

        realtime.pause_updates();
        canvas.api.store_buy('sticker', item_id).done(function (result) {
            canvas_effects.make_it_rain(
                self.shop.find('.balance img'),
                item_cost,
                function (i) {
                    num1_count.text(starting_balance - i);
                },
                function () {
                    canvas_effects.short_message("PURCHASED!", offset.left + sticker_wrapper.width()/2, offset.top + sticker_wrapper.height()/2).css({ zIndex: 105 }, 300);
                    realtime.unpause_updates();
                    sticker_pack.increase_sticker_count_flourish(item_id);
                }
            );
        })
    });

    this.shop.find('.buy').each(function (i, buy) {
        stickers.check_for_animation($(buy).data('item-id'), $(buy).data('item-name'));
    });

    return this.shop;
};

