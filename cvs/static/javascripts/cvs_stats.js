function loadChart(action) {
    $.post(
        action,
        $("#date_range_form").serialize(),
        function(data) {
            $('#chart_container').html(data);
        }
    )
}