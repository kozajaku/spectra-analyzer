$(document).ready(function () {
    //setup namespace for socketio
    var namespace = "/downloader";
    //connect to the socketio server
    var socket = io.connect(location.protocol + "//" + document.domain + ":" + location.port + namespace, {
        "path": "/spectra-analyzer/socket.io"
    });

    var parseSuccess = true;
    var datalinkAvailable;
    var spectraList;
    var downloadIndex = 0;

    $.cookie = function (name, value) {
        document.cookie = encodeURIComponent(name) + '=' + encodeURIComponent(value) + "; path=/";
    };

    function showParseResult() {
        if (parseSuccess) {
            $('.parse-fail').hide();
            $('.parse-success').show();
        } else {
            $('.parse-fail').show();
            $('.parse-success').hide();
        }
    }

    function votableSet(set) {
        if (set) {
            $("#vot-selected").removeClass("hidden");
            $("#vot-unselected").addClass("hidden");
        } else {
            $("#vot-unselected").removeClass("hidden");
            $("#vot-selected").addClass("hidden");
        }
    }

    function showLinkInputType() {
        $('#vot-input-link').removeClass("hidden");
        $('#vot-input-upload').addClass("hidden");
        $('#vot-input-direct').addClass("hidden");
    }

    function showUploadInputType() {
        $('#vot-input-link').addClass("hidden");
        $('#vot-input-upload').removeClass("hidden");
        $('#vot-input-direct').addClass("hidden");
    }

    function showDirectInputType() {
        $('#vot-input-link').addClass("hidden");
        $('#vot-input-upload').addClass("hidden");
        $('#vot-input-direct').removeClass("hidden");
    }

    function showProgress() {
        $('.progress').removeClass("hidden");
        //disable buttons
        $('.continue-btn').prop("disabled", true);
    }

    function hideProgress() {
        $('.progress').addClass("hidden");
        //enable buttons
        $('.continue-btn').prop("disabled", false);
    }

    function sendVotableText(text) {
        //show progress bar
        showProgress();
        socket.emit("votable_text", text);
    }

    function sendVotableUrl(url) {
        //show progress bar
        showProgress();
        socket.emit("votable_url", url);
    }

    function renderSpectraList() {
        var $select = $('select[name=spectra]');
        $select.html('');
        var $option;
        for (var i = 0; i < spectraList.length; i++) {
            $option = $('<option>', {'value': spectraList[i][0]})
                .html(spectraList[i][1]);
            if (i == 0) {
                $option.prop('selected', true);
            }
            $select.append($option);
        }
        $select.prop('size', spectraList.length > 20 ? 20 : spectraList.length);
    }

    function renderDataLink(datalink) {
        var $form = $('#datalink-form');
        var $checkbox = $('<input>', {'type': 'checkbox', 'name': 'use-datalink'}).prop('checked', true);
        $checkbox.change(function () {
            if ($(this).prop('checked')) {
                $form.find('input[type=text]').prop('disabled', false);
                $form.find('select').prop('disabled', false);
            } else {
                $form.find('input[type=text]').prop('disabled', true);
                $form.find('select').prop('disabled', true);
            }
        });
        $form.html('');
        $form.append($checkbox);
        $form.append(' Use DataLink protocol<br>');
        for (var i = 0; i < datalink.length; i++) {
            var param = datalink[i];
            $form.append('<label>' + param['name'] + ':</label><br>');
            if (param['select']) {
                var $select = $('<select>', {'name': param['name']});
                var $option = $('<option>', {'value': ''}).html('Nothing selected');
                $select.append($option);
                for (var j = 0; j < param.options.length; j++) {
                    var option = param['options'][j];
                    $option = $('<option>', {'value': option['value']})
                        .html(option['name']);
                    $select.append($option);
                }
                $form.append($select);
            } else {
                $form.append($('<input>',
                    {'type': 'text', 'name': param['name']}));
            }
            $form.append('<br>');
        }
        $('.datalink-available').show();

    }

    function downloadSpectra() {
        //get selected spectra ids
        var spectraIds = [];
        var $spectra = $('select[name=spectra]');
        $spectra.find('option:selected').each(function () {
            spectraIds.push($(this).val());
        });
        if (spectraIds.length == 0) {
            alert("You must select at least one spectrum to download");
            return;
        }
        var message = {"spectra": spectraIds};
        //get datalink params
        if (datalinkAvailable &&
            $('input[type=checkbox][name=use-datalink]').prop('checked')) {
            message['use-datalink'] = true;
            var datalink = {};
            var $form = $('#datalink-form');
            var appendParam = function () {
                datalink[$(this).prop('name')] = $(this).val();
            };
            $form.find('input[type=text]').each(appendParam);
            $form.find('select').each(appendParam);
            message['datalink'] = datalink;
        } else {
            message['use-datalink'] = false;
        }
        //get target directory
        message['directory'] = $('#directory').val();
        //set directory as a cookie
        $.cookie("last-directory", message['directory']);
        //prepare lines in a table
        downloadIndex = 0;
        $('#download-log-body').html('');
        //emit message
        socket.emit('download_spectra', message);
//                window.history.pushState(null, "Downloading", "/downloading")
    }

    function setView(id) {
        if (id == 1) {
            $('.view2').addClass('hidden');
            $('.view1').removeClass('hidden');
        } else if (id == 2) {
            $('.view1').addClass('hidden');
            $('.view2').removeClass('hidden');
        }
    }

    //add votable input type change listeners
    $('input[type=radio][name=vot-input-type]').change(function () {
        if (this.value == 'link') {
            showLinkInputType();
        }
        else if (this.value == 'upload') {
            showUploadInputType();
        } else if (this.value == 'direct') {
            showDirectInputType();
        }
    });

    //add listener on url-process button click
    $('#url-process').click(function () {
        var url = $('#ssap-url').val();
        sendVotableUrl(url);
    });

    //add listener for file-upload button click
    $('#file-upload').click(function () {
        var files = $('#vot-file')[0].files;
        if (files.length == 0) {
            alert("Select VOTABLE file first!")
        } else {
            var file = files[0];
            var reader = new FileReader();
            reader.onload = function (e) {
                var result = e.target.result;
                sendVotableText(result);
            };
            reader.readAsText(file);
        }
    });
    //add listener for text area
    $('#direct-process').click(function () {
        var content = $('#ssap-textarea').val();
        sendVotableText(content);
    });
    //add listener for back buttons
    $('.back-btn').click(function () {
        votableSet(false)
    });
    //add listener for download button
    $('.download-btn').click(function () {
        downloadSpectra();
        setView(2);
    });
    //add listener for select all button
    $('#select-all-btn').click(function () {
        $('select[name=spectra] option').each(function () {
            $(this).prop('selected', true);
        });
    });
    //register socketio events
    socket.on("votable_parsed", function (response) {
        var link;
        //render result table
        if (response['success']) {
            parseSuccess = true;
            if (response['link_known']) {
                link = response['link'];
                $('#resource-url').html(
                    $('<a>', {"href": link}).html(link)
                );
            } else {
                $('#resource-url').html("unknown");
            }
            $('#record-count').html(response['record_count']);
            $('#datalink-available').html(response['datalink_available']);
            var $queryStatus = $('#query_status');
            $queryStatus.html(response['query_status']);
            if (response['query_status'] == 'OK') {
                $queryStatus.removeClass('fail').addClass('success');
            } else {
                $queryStatus.removeClass('success').addClass('fail');
            }
            spectraList = response['spectra'];
            renderSpectraList();
            if (response['datalink_available']) {
                datalinkAvailable = true;
                renderDataLink(response['datalink']);
            } else {
                datalinkAvailable = false;
                $('.datalink-available').hide();
            }
            $('#directory').val(response['directory']);
        } else {
            parseSuccess = false;
            if (response['link_known']) {
                link = response['link'];
                $('#resource-url-fail').html(
                    $('<a>', {"href": link}).html(link)
                );
            } else {
                $('#resource-url-fail').html("unknown");
            }
            $('#error-message').html(response['exception']);
        }
        hideProgress();
        showParseResult();
        votableSet(true);
    });

    socket.on("spectrum_downloaded", function (response) {
        var $logBody = $('#download-log-body');
        var $name = $('<td>').html(response['file_name']);
        var $downloadLink = $('<td>').append($('<a>', {'href': response['url']}).html('link'));
        var $state;
        var $problem;
        if (response.success) {
            $state = $('<td>').addClass('success').html("SUCCESS");
            $problem = $('<td>');
        } else {
            $state = $('<td>').addClass('fail').html("FAILED");
            $problem = $('<td>').html(response['exception']);
        }
        console.log('appending');
        $logBody.append($('<tr>').append($name).append($downloadLink).append($state).append($problem));
    });

    socket.on("spectra_downloaded", function (success) {
        if (success) {
            $('#download-status').html('All spectra successfully downloaded').addClass('success');
        } else {
            $('#download-status').html('At least one spectrum was not downloaded').addClass('fail');
        }
        $('.download-progress').hide();
    });

    socket.on('disconnect', function () {
        alert("Disconnected from the server. Please refresh the page.");
    });

    //select first radio button - some browser caches the state
    $('input[type=radio][name=vot-input-type][value=link]').prop('checked', true);
    hideProgress();//just to be sure
});