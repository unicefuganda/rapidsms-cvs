function deleteFacility(elem, pk, name) {
    if (confirm('Are you sure you want to remove ' + name + '?')) {
        $(elem).parents('tr').remove();
        $.post('../facility/' + pk + '/delete/', function(data) {});
    }
}

function editFacility(elem, pk) {
    overlay_loading_panel($(elem).parents('tr'));
    $(elem).parents('tr').load('../facility/' + pk + '/edit/', '', function () {
        $('#div_panel_loading').hide();
    });
}

function newFacility(elem) {
	overlay_loading_panel($(elem).parents('tr'));
	$(elem).parents('tr').load('../facility/new','', function () {
		$('#div_panel_loading').hide();
	});
}

function submitForm(link, action, resultDiv) {
    form = $(link).parents("form");
    form_data = form.serializeArray();
    resultDiv.load(action, form_data);
}

function update_facility_district(elem) {
	facility_pk = $(elem).parents("tr").children(".facility").attr('id').substring(4);
    $('#facility_locations').empty();
    district_pk = $('#id_facility_district').val();
    $('#facility_locations').load('../facility/' + facility_pk + '/locations/edit/' + district_pk + '/');
}
function detail_elem(elem){
    $('#contactArea').html("");
    id = elem.id.split('_')[1];
    $('#popup_heading').html('Facility Details');
    $.get(
        '../facility/'+id+'/detail/',
        {},
        function(data){
            $('#contactArea').html(data);
        }
    );
    centerPopup();
    loadPopup();
}

function show_complete_reports(elem){
    $('#contactArea').html("");
    id = elem.id.split('_')[1];
    $('#popup_heading').html('Facility Report Completeness');
    $.get(
        '../facility/' + id + '/completeness/',
        {},
        function(data){
            $('#contactArea').html(data);
        }
    );
    centerPopup();
    loadPopup();
}

function send_sms(elem){
    $('#contactArea').html("");
    id = elem.id.split('_')[1];
    $('#popup_heading').html('Send SMS');
    $.get(
        '../facility/' + id + '/sendsms/',
        {},
        function(data){
            $('#contactArea').html(data);
        }
    );
    centerPopup();
    loadPopup();
}
/*
$('#sendsms').click(function(){
    return;
});
*/
