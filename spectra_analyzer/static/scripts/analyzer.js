$(document).ready(function () {
    //setup namespace for socketio
    var namespace = "/analyzer";
    //connect to socketio server
    var socket = io.connect(location.protocol + "//" + document.domain + ":" + location.port + namespace);
    var loadedDirectoryPath = "";
    var loadedDirectory;
    var scales;
    //on follow path button click event
    $('#follow-path').click(function () {
        var path = $('#spectrum-path').val();
        socket.emit('change_path', path);
    });

    function createSlider(id, label, from, to, onchange) {
        var $div = $('<div>');
        $div.append($('<label>', {'for': id}).html(label)).append($('<br>'));
        var $input = $('<input>', {
            'type': 'range',
            'min': from,
            'max': to,
            'value': 0,
            'id': id
        });
        $div.append($input);
        var $span = $('<span>').html("0");
        $div.append($span);
        $input.change(function () {
            $span.html($(this).val());
            onchange($(this).val());
        });
        return $div;
    }

    function notifySliderChanged(){
        //get values from sliders
        var freq0 = Number($('#freq0').val());
        var wSize = Number($('#wSize').val());
        showProgressSliders();
        socket.emit('slider_changed', {'freq0': freq0, 'wSize': wSize});
    }

    $('.sliders').append(createSlider('freq0', 'Frequency shift:', 0, 50, function (val) {
        //change slider boundaries
        var max = scales - 1 - val;
        max = max < 0 ? 0 : max;
        $('#wSize').prop('max', max);
        notifySliderChanged();
    })).append(createSlider('wSize', 'Window size:', 0, 50, function (val) {
        var max = scales - 1 - val;
        max = max < 0 ? 0 : max;
        $('#freq0').prop('max', max);
        notifySliderChanged();
    }));

    function showProgress() {
        $('.progress').removeClass('hidden');
    }

    function hideProgress() {
        $('.progress').addClass('hidden');
    }
    function showProgressSliders() {
        $('.progress-sliders').removeClass('hidden');
    }

    function hideProgressSliders() {
        $('.progress-sliders').addClass('hidden');
    }

    function registerRowClickEvents() {
        $('#directory-listing').find('tr').click(function () {
            var rowId = $(this).prop('id');
            var id = Number(rowId.substr(3));
            var newPath = loadedDirectory[id]['path'];
            socket.emit("change_path", newPath)
        });
    }

    function refreshPath(data) {
        if (data['invalid']) {
            alert('The path ' + data['path'] + ' is invalid');
            $('#spectrum-path').val(loadedDirectoryPath);
            return;
        }
        loadedDirectoryPath = data['path'];
        loadedDirectory = data['directory'];
        var $tbody = $('#directory-listing');
        $tbody.html('');
        var item;
        for (var i = 0; i < loadedDirectory.length; i++) {
            item = loadedDirectory[i];
            var $tr = $('<tr>', {'id': 'row' + i});
            if (item['selected']) {
                $tr.addClass('selected-row');
                showProgress();
                socket.emit('analyze_file', item['path']);
            }
            if (item['is_file']) {
                $tr.addClass('file');
                $tr.append($('<td>').html('F'));
                //append file name
                $tr.append($('<td>').addClass('name').html(item['name']));
                //append last mod
                $tr.append($('<td>').html(item['modified']));
                //append size
                $tr.append($('<td>').html(item['size']));
            } else {
                $tr.append($('<td>').html('D'));
                //append directory name
                $tr.append($('<td>').addClass('name').html(item['name']));
                $tr.append($('<td>'));
                $tr.append($('<td>'));
            }
            $tbody.append($tr);
        }
        $('#spectrum-path').val(loadedDirectoryPath);
        registerRowClickEvents();
    }

    socket.on("directory_info", function (response) {
        refreshPath(response);
    });

    socket.on("file_analyzed", function (response) {
        hideProgress();
        if (response['invalid']) {
            $('.file-analyze').addClass('hidden');
            var $invalid = $('.file-invalid');
            $invalid.removeClass('hidden');
            $invalid[0].scrollIntoView();
        } else {
            $('.file-invalid').addClass('hidden');
            var $view = $('.file-analyze').removeClass('hidden');
            $('.spectrum-name').html(response['file_name']);
            $('#spectrum-plot').prop('src', 'data:image/png;base64,' + response['spectrum_img']);
            $('#freq0').val(response['freq0']).find('~ span').html(response['freq0']);
            $('#wSize').val(response['wSize']).find('~ span').html(response['wSize']);
            scales = response['scales'];
            $('#cwt-plot').prop('src', 'data:image/png;base64,' + response['cwt_img']);
            $('#transformation-plot').prop('src', 'data:image/png;base64,' + response['transformation_img']);
            $view[0].scrollIntoView({behavior: 'smooth'});
        }
    });

    socket.on("transformation_updated", function (response) {
        $('#transformation-plot').prop('src', 'data:image/png;base64,' + response);
        hideProgressSliders();
    });

});