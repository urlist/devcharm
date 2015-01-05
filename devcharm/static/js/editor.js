$(function () {
    'use strict';

    // Update threshold, to avoid destroying the CPU
    var THRESHOLD = 1000,
        ARTICLE_ID = $('[name="article_id"]').val() || null,
        IS_MINE = $('form.is-mine').length,
        IS_PUBLISHED = $('form.is-published').length,
        first, firstTs, toSave, limitedUpdate;

    function parse () {
        // This function parses the markdown and extracts
        // stuff like title, punchline etc...
        // performance wise is quite shitty, but it's super
        // simple to do.

        var text         = editor.getValue(),
            tokens       = marked.lexer(text),
            html         = $('<div>' + marked(text) + '</div>'),
            firstSection = text.indexOf('##'),

            data = {
                title       : $.trim(html.find('h1:nth(0)').text()),
                punchline   : $.trim(html.find('blockquote:nth(0)').text()),
                content     : firstSection != -1 ? $.trim(text.substring(firstSection)) : ''
            };

        // Dear Javascript God please forgive me. I know it's shit.
        for (var i = 0, pos = 0, found = false; i < tokens.length && !found; i++)
            if (tokens[i].type == 'paragraph' && pos++)
                found = true;

        data.description = found ? tokens[i-1].text : '';

        return data;
    }


    function updatePreview (data) {
        // update the title in the preview
        preview.find('h1').text(data.title);
        preview.find('h2').text(data.punchline);
        preview.find('.article-description').html(marked(data.description));

        // update the main content
        preview.find('.article-content').html(marked(data.content));

        // check for title
        if (!data.title.length)
            preview.find('h1').html('<a href="#" class="js-add-title">Click to add a title</a>');

        // check for punchline
        if (!data.punchline.length)
            preview.find('h2').html('<a href="#" class="js-add-punchline">Click to add a punchline</a>');

        // check for content
        if (!data.content.length)
            preview.find('.article-content').html('<a href="#" class="js-add-content">Click to add content</a>');
    }

    function highlightWorkingSection () {
        if (!section)
            return;

        var current = $(preview.find('h2').get(section));
        window.CURRENT = current;

        preview.find('.article-description').addClass('inactive');
        preview.find('h2').addClass('inactive');
        preview.find('ul').addClass('inactive');
        current.removeClass('inactive').next().removeClass('inactive');
        preview.scrollTop(current.offset().top - 100);
    }

    function update () {
        updatePreview(parse());

        // open links in a new tab/window
        $('.js-content a').attr('target', '_blank');
    }


    function syncScroll (scrollFrom, scrollTo, heightFrom, heightTo) {
        var relative = scrollFrom.scrollTop() / (heightFrom.height() - heightViewport.height()),
            now      = new Date();

        if (!first || now - firstTs > 1000) {
            firstTs = new Date();
            first = scrollFrom;
        }

        scrollTo.scrollTop((heightTo.height() - heightViewport.height()) * relative);
    }

    function unfoldSelected () {
        var lines = editor.getValue().split('\n'),
            line  = 0,
            counter;

        if (!section)
            return;

        counter = section;

        for (line = 0; line < lines.length && counter; line++)
            if (lines[line].match(/^## /))
                counter--;

        if (!counter) {
            session.foldAll();
            session.unfold(line);
            editor.moveCursorTo(line);
        }
    };


    var // Editor related variables
        editor  = ace.edit('aceeditor'),
        preview = $('#preview'),
        session = editor.getSession(),

        // Scrollbars
        scrollbarEditor  = $('#aceeditor .ace_scrollbar'),
        scrollbarPreview = $('#preview'),

        // Heights
        heightEditor  = $('#aceeditor .ace_scrollbar-inner'),
        heightPreview = $('#preview .preview-wrapper'),
        heightViewport = $('.editor-main'),

        // Params
        sectionParam = getParameterByName('section'),
        section = sectionParam.length > 0 ? parseInt(sectionParam) : null;


    limitedUpdate = _.throttle(update, THRESHOLD);

    editor.setTheme('ace/theme/monokai');
    session.setMode('ace/mode/markdown');
    session.setUseWrapMode(true);
    editor.setShowPrintMargin(false);

    session.on('change', function () {
        toSave = true;
        limitedUpdate();
    });

    $('[name="keybinding"]').change(function (e) {
        var mode = $(e.target).val();

        if (mode == 'noop')
            return;

        if (mode == 'default')
            mode = null;

        editor.setKeyboardHandler(mode);
    });

    $(window).bind('beforeunload', function (e) {
        if (toSave)
            return 'You have unsaved changes.';
    });

    preview.on('click', '.js-add-title', function (e) {
        session.insert({ row:0, column:0 }, '# This is the title\n\n');
        e.preventDefault();
    });

    preview.on('click', '.js-add-punchline', function (e) {
        session.insert({ row:2, column:0 }, '> This is a punchline\n\n');
        e.preventDefault();
    });

    preview.on('click', '.js-add-description', function (e) {
        session.insert({ row:4, column:0 }, 'This is a nice **description**\n\n');
        e.preventDefault();
    });

    preview.on('click', '.js-add-content', function (e) {
        session.insert({ row:6, column:0 }, '## A new section\n\n- [Link title](http://example.com) is an example of title\n\n- [Devcharm](http://devcharm.com/) is a nice place for developers.');
        e.preventDefault();
    });

    if (!section) {
        scrollbarEditor.scroll(function (e) {
            syncScroll(scrollbarEditor, scrollbarPreview, heightEditor, heightPreview);
        });
    }

    scrollbarPreview.scroll(function (e) {
        //syncScroll(scrollbarPreview, scrollbarEditor, heightPreview, heightEditor);
    });


    $('.js-save').click(function (e) {
        var button = $(e.target),
            form = $('form'),
            action = form.attr('action'),
            data = form.serializeArray(),
            req;

        data.push({name: 'raw_content', value: EDITOR.getValue()});
        req = $.post(action, data);

        //$t.addClass('do--OK');
        //$t.width(width);

        req.done( function (data) {
                var oldText = button.text();
                toSave = false;

                if (!ARTICLE_ID) {
                    sendEvent('engagement,write-new-success,oners,20', function () { window.location = data.edit_url; });
                } else if (!IS_PUBLISHED) {
                    sendEvent('engagement,save-draft,oners,50');
                } else {
                    if (IS_MINE) {
                        sendEvent('engagement,author-save-changes,oners,20');
                    } else {
                        sendEvent('engagement,contrib-save-changes,niners,20');
                    }
                }

                form.attr('action', data.edit_url);
                $('.js-publish').attr('data-endpoint', data.publish_url);
                $('.js-delete').attr('data-endpoint', data.delete_url);
                button.text('Saved!');
                window.setTimeout(function () { button.text(oldText); }, 1000);
            })

            .fail( function () {
                alert('Oops, an error occurred. Try again.');
            });

        e.preventDefault();
    });


    $('.js-publish').click(function (e) {
        var $t  = $(e.target),
            url = $t.data('endpoint'),
            req = $.post(url);

        $t.addClass('disabled');

        req
            .done( function (data) {
                sendEvent('engagement,publish,oners,80', function () { window.location = data.url; });
            })

            .fail( function () {
                alert('Oops, an error occurred. Try again.');
            });

        e.preventDefault();
    });


    $('.js-delete').click(function (e) {
        var $t  = $(e.target),
            url = $t.data('endpoint'),
            req;

        if (!confirm('Are you sure you want to delete this page?'))
            return;

        $t.addClass('disabled');

        req = $.post(url                                                                                                                                                                                                                                                                                                                                                                )
            .done( function (payload) {
                window.location = '/profiles';
            })

            .fail( function () {
                alert('Oops, an error occurred. Try again.');
            });

        e.preventDefault();
    });

    update();

    window.setTimeout(function () {
        unfoldSelected();
        highlightWorkingSection();
    }, 200);

    window.EDITOR = editor;
});

