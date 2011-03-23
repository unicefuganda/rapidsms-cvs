function loadChart(action) {
    $.post(
        action,
        $("#date_range_form").serialize(),
        function(data) {
            
            $('#chart_container').html(data);
        }
    )
}

function tickEvery(num){

    $('.ui-slider span.ui-slider-tic').each(function(index,elem)
    {
        if((index + 1) % num == 0)
        {
            $(elem).css('display','block');
        }


    }


            );

}