function deleteReporter(pk, name) {
    if (confirm('Are you sure you want to remove ' + name + '?')) {
        $('#row_' + pk).parent().remove();
        $.post('../reporter/' + pk + '/delete/', function(data) {

        });
    }
}

function editReporter(pk) {
    $('#row_' + pk).parent().load('../reporter/' + pk + '/edit/');
}

function submitForm(link, action, resultDiv) {
    form = $(link).parents("form");
    form_data = form.serializeArray();
    resultDiv.load(action, form_data);
}
