(function () {

    'use strict';

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", $.cookie('csrftoken'));
            }
        }
    });

    // http://stackoverflow.com/questions/610406/javascript-equivalent-to-printf-string-format/4256130#4256130
    // author: Filipiz
    String.prototype.format = function () {
        var formatted = this;
        for (var i = 0; i < arguments.length; i++) {
            var regexp = new RegExp('\\{'+i+'\\}', 'gi');
            formatted = formatted.replace(regexp, arguments[i]);
        }
        return formatted;
    };


    // http://stackoverflow.com/a/901144/597097
    window.getParameterByName = function (name) {
        name = name.replace(/[\[]/, "\\\[").replace(/[\]]/, "\\\]");
        var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
            results = regex.exec(location.search);
        return results == null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
    };


    window.removeURLParameter = function (parameter) {
        //prefer to use l.search if you have a location/link object
        var url = window.location.href;
        var urlparts = url.split('?');

        if (urlparts.length >= 2) {
            var prefix = encodeURIComponent(parameter) + '=';
            var pars = urlparts[1].split(/[&;]/g);

            //reverse iteration as may be destructive
            for (var i = pars.length; i-- > 0;) {
                //idiom for string.startsWith
                if (pars[i].lastIndexOf(prefix, 0) !== -1) {
                    pars.splice(i, 1);
                }
            }

            url = urlparts[0];

            if (pars.length > 0)
                url += '?' + pars.join('&');
            return url;
        } else {
            return url;
        }
    };


    window.popRef = function () {
        var ref = getParameterByName('ga_ref');

        if (ref)
            history.replaceState({}, '', removeURLParameter('ga_ref'));

        return ref;
    };

}) ();

$(function () {
    $('a[data-ga]').click(function () {
        var elem = $(this),
            url = elem.attr('href'),
            data = elem.attr('data-ga').split(',');
        ga('send', {
            'hitType': 'event',
            'eventCategory': data[0],
            'eventAction': data[1],
            'eventLabel': data[2],
            'eventValue': parseInt(data[3]) || null,
            'nonInteraction': true,
            'hitCallback': function () { window.location.href = url; }
        });
    });

    window.sendEvent = function (s, c) {
        var data = s.split(',');
        ga('send', {
            'hitType': 'event',
            'eventCategory': data[0],
            'eventAction': data[1],
            'eventLabel': data[2],
            'eventValue': parseInt(data[3]) || null,
            'nonInteraction': true,
            'hitCallback': c || function () {}
        });
    };
});

