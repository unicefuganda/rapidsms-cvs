function deleteReporter(elem, pk, name) {
    if (confirm('Are you sure you want to remove ' + name + '?')) {
        $(elem).parents('tr').remove();
        $.post('../reporter/' + pk + '/delete/', function(data) {});
    }
}

function editReporter(elem, pk) {
    overlay_loading_panel($(elem).parents('tr'));
    $(elem).parents('tr').load('../reporter/' + pk + '/edit/', '', function () {
        $('#div_panel_loading').hide();    
    });
}

function submitForm(link, action, resultDiv) {
    form = $(link).parents("form");
    form_data = form.serializeArray();
    resultDiv.load(action, form_data);
}

function update_district(elem) {
	reporter_pk = $(elem).parents("tr").children(".reporter").attr('id').substring(4);
    $('#reporter_facility').empty();
    $('#reporter_village').empty();
    district_pk = $('#id_reporter_district').val(); 
    $('#reporter_facility').load('../reporter/' + reporter_pk + '/facilities/edit/' + district_pk + '/');
    $('#reporter_village').load('../reporter/' + reporter_pk + '/locations/edit/' + district_pk + '/');            
}
