$(function () {

    $('.js-nav-mobile-trigger').click(function (e) {
        $('.js-nav-mobile').toggleClass('active');
    });

    // Landing Page

    var hideClass        = 'hide',

        $signupButton = $('.js-signup-trigger'),
        $submitButton = $('.js-submit-trigger'),

        $signupFormTrigger = $('.js-form-signup-trigger'),
        $submitFormTrigger = $('.js-form-submit-trigger'),

        $signupForm = $('.js-form-signup'),
        $submitForm = $('.js-form-submit');

    window.marked && window.marked.setOptions({
        sanitize: true
    });

    $signupForm.hide();
    $submitForm.hide();

    $('.js-signup-trigger').click(function (e) {
        $signupForm.slideDown();
        $submitForm.slideUp();

        $(this).closest('.page-actions-home').slideUp();

        e.preventDefault();
    });

    $('.js-submit-trigger').click(function (e) {
        $submitForm.slideDown();
        $signupForm.slideUp();

        $(this).closest('.page-actions-home').slideUp();

        e.preventDefault();
    });


    // List Page

    if ($('#aceeditor-preview').length == 0)
        $(':not(#aceeditor-preview) .page-content a').click(function (e) {
            console.log('sdafasdf');
                ga('send', 'event', 'link', 'open');
        });

    $('.js-karma-give').click(function (e) {
        var $me = $(e.target),
            $p  = $me.parent(),
            $cnt = $p.find('.js-karma-count'),
            tot = parseInt($cnt.text(), 10);

        $cnt.addClass("do--anim");

        $me.hide();
        $p.find('.js-karma-thanks').removeClass('hide');
        $p.find('.js-karma-count').text(tot + 1);

        // send to google analytics
        if (typeof ga !== 'undefined')
            ga('send', 'event', 'cta', 'kudos', window.location.pathname);

        // send to our DB
        $.get($me.attr('href'));

        e.preventDefault();
    });


    // open links inside Page and Editor in a new tab/window
    $('.js-content a').attr('target', '_blank');


    // Small Editor

    // open the editor
    $('.js-smalleditor-edit').on('click', function (e) {
        $('.js-smalleditor').addClass('smalleditor--active');
        $('.js-smalleditor').find('.js-smalleditor-value').trigger('focus');
        e.preventDefault();
    });

    // close the editor
    $('.js-smalleditor-close').on('click', function (e) {
        $('.js-smalleditor').removeClass('smalleditor--active');

        e.preventDefault();
    });

    // save action
    $('.js-smalleditor-save').on('click', function (e) {
        var endpoint = $(e.target).data('endpoint'),
            toSave   = $('.js-smalleditor-value'),
            toSaveVal = toSave.val(),
            req;

        $('.js-smalleditor').removeClass('smalleditor--active');

        req = $.post(endpoint, { bio: toSaveVal });

        req.fail( function () {
                alert('Oops, an error occurred. Try again.');
            });

        $('.js-smalleditor-data').html(marked(toSaveVal));

        e.preventDefault();
    });


});
