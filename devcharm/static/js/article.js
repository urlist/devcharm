$(function() {
    function addEditButtons () {
        var editUrl = $('.js-edit-url').attr('href');

        $('.article-content h2').each(function (i) {
            var editSectionUrl = editUrl + '?section=' + (i + 1);
            $(this).after('<div class="edit-article-button">[ <a href="' + editSectionUrl + '" data-ga="engagement,edit,niners,10">edit</a> ]</div>');
        });
    }

    var IS_WIKI = $('article.is-wiki').length != 0;

    $('.article-content a').each(function (i) {
        $(this).attr('target', '_blank');
    });

    $('.article-content a').click(function (i) {
        sendEvent('engagement,outlink,ninetiers,5');
    });

    if (IS_WIKI)
        addEditButtons();
});


$(function() {
    $('.article-actions form').submit(function () {
        var me = $(this);
        sendEvent('engagement,kudo,ninetiers,5');

        $.post(me.attr('action'), me.serialize(), function (data) {
            $('.kudos-count').text(data);
        });
        return false;
    });
});


$(function () {
    $('.banner-close').click(function () {
        $.cookie('bannertop', 'hide', { expires: 3 });
        $('.banner-cta-container').hide();
        return false;
    });

    if ($.cookie('bannertop') == 'hide')
        $('.banner-cta-container').hide();
});

