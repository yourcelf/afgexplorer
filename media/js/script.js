function linebreaks(str) {
    return str.replace(/\n/g, "<br /><br />");
}
function fix_amps(str) {
    // Fix &amp;quot; nonsense.
    while (str.indexOf("&amp;") != -1) {
        str = str.replace(/&amp;/g, "&");
    }
    str = str.replace(/&(?!(#[a-z\d]+|\w+);)/gi, "&amp;");
    return str;
}
function linkify(text, phrases) {
    // Get character ranges over which links are valid.
    var flat = text.replace(/\n/g, " ").toUpperCase();
    var beginnings = {}; // beginning position: [ rid, rid, rid ]
    var endings = {};    // ending position: [ rid, rid, rid ]
    for (var phrase in phrases) {
        var start = flat.indexOf(phrase);
        var end = start + phrase.length;
        if (beginnings[start] == undefined) {
            beginnings[start] = [];
        }
        // add all links to this beginning position
        beginnings[start] = beginnings[start].concat(phrases[phrase]);
        if (endings[end] == undefined) {
            endings[end] = [];
        }
        endings[end] = endings[end].concat(phrases[phrase]);
    }
    // Split the text into spans for the ranges.
    var out = [];
    var within = []; // list of rid's we are currently in range of
    for (var i = 0; i < text.length; i++) {
        if (endings[i] || beginnings[i]) {
            if (within.length > 0) {
                out.push("</span>");
            }
            if (endings[i]) {
                // remove everything in 'within' that is in 'endings[i]' 
                for (var j = 0; j < endings[i].length; j++) {
                    var pos = $.inArray(endings[i][j], within);
                    if (pos != -1) {
                        within.splice(pos, 1);
                    }
                }
            }
            if (beginnings[i]) {
                for (var j = 0; j < beginnings[i].length; j++) {
                    if ($.inArray(beginnings[i][j], within) == -1) {
                        within.push(beginnings[i][j]);
                    }
                }
            }
            if (within.length > 0) {
                out.push("<span class='links ");
                out.push($.map(within, function(w) { return "key" + w }).join(" "));
                out.push(" numlinks" + Math.min(10, within.length));
                out.push("'>");
            }
        }
        out.push(text.substring(i, i+1));
    }
    return [out.join("")];
}
function displayText(tokens, div, popup_url, loading_text) {
    for (var i = 0; i < tokens.length; i++) {
        $(div).append(linebreaks(fix_amps(tokens[i])));
    }
    // Callback for links
    $(div).parent().bind("click", function() { 
        $(".popup").remove() 
        clickout = false;
    });
    $(div).find(".links").bind("click", function(event) {
        event.stopPropagation();
        $(".popup").remove();
        var content = $(document.createElement("div")).attr("class", "content").html(
            loading_text
        );
        var clicked = this.innerHTML.toUpperCase().replace(/\s+$/g, '').replace(/^\s+/g, '');
        var pop = $(document.createElement("div")).attr("class", "popup").append(
                $(document.createElement("a")).attr("class", "close")
                    .html("close")
                    .bind("click", function() { $(this).parent().remove(); })
            ).append(content);
        var offset = $(this).offset();
        var parent = $(this).parent(); 
        var parOffset = parent.offset();
        var newOffset = {
            'left': parOffset.left + 10,
            'top': offset.top + 15
        };
        pop.hide();
        $("body").append(pop);
        pop.fadeIn();
        pop.width($(this).parent().width() - 30);
        pop.offset(newOffset);
        pop.offset(newOffset); // chrome/safari bug; have to do this twice
        var ids = [];
        $.each(this.className.split(' '), function(i, classname) {
            var match = /key(\d+)/.exec(classname);
            if (match) {
                ids.push(parseInt(match[1]));
            }
        });
        var texts = [];
        for (var i = 0; i < ids.length; i++) {
            var bestText = "";
            var possibleTexts = linkPhrases[ids[i]];
            for (var j = 0; j < possibleTexts.length; j++) {
                var ptext = possibleTexts[j].replace(/\s+$/g, '').replace(/^\s+/g, '');
                if (ptext.length > bestText.length && ptext.indexOf(clicked) != -1) {
                    bestText = ptext;
                }
            }
            texts.push(escape(bestText));
        }
        $.ajax({
            type: "GET",
            url: popup_url,
            data: { 
                'rids': ids.join(","), 
                'clicked': this.innerHTML, 
                'texts': texts.join(",")
            },
            success: function(html) {
                content.html(html);
            },
            error: function() {
                content.html("Error communicating with server.");
            }
        });

    });
}

