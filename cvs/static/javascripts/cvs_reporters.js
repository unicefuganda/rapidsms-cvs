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

function newReporter(elem) {
	// ajax load in the new reporter view
	overlay_loading_panel($(elem).parents('tr'));
	$(elem).parents('tr').load('../reporter/new', '', function () {
		$('#div_panel_loading').hide();
	});
}

/**
 * Post the form to the edit reporter view, then ajax load the results into the 
 * target element (see cvs.views.reporter and cvs/templates/reporter/partials)
 * @param link - the save link that was clicked
 * @param action - the url to post to
 * @param resultElem - the element to load the results into (usually a TR)
 */
function submitForm(link, action, resultElem) {
    form = $(link).parents("form");
    form_data = form.serializeArray();
    resultElem.load(action, form_data);
}

/**
 * Ajax load new facility and location drop-downs, progressively filtered
 * by the new district value (see cvs.views.reporter and cvs/templates/reporter/partials)
 * @param elem - the select box (for districts) that was changed
 */
function update_district(elem) {
	reporter_pk = $(elem).parents("tr").children(".reporter").attr('id').substring(4);
    $('#reporter_facility').empty();
    $('#reporter_village').empty();
    district_pk = $('#id_reporter_district').val(); 
    $('#reporter_facility').load('../reporter/' + reporter_pk + '/facilities/edit/' + district_pk + '/');
    $('#reporter_village').load('../reporter/' + reporter_pk + '/locations/edit/' + district_pk + '/');            
}
function update_district2(elem) {
	parent_td = $(elem).parents("td");
    district_pk = $(elem).val(); 
    $('.ffacility').parents('td').load('../reporter/facilities/edit/' + district_pk + '/');           
}
