$(function () {
    var old_line = $('.story-task-row').find(".title:contains('michael'), .title:contains('Michael')").closest('.story-task-row').hide();
    var line = $('<tr></tr>').attr('id', 'michael_line');
    var line_td = $('<td></td>').attr({id: 'michael_line_td', colspan: 6}).text('Backlog');
    line.append(line_td);
    old_line.before(line);
});

