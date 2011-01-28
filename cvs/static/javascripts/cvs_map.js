
var layers=[];
var base_url;
var map;
var descriptions=[];
var markers=[];
var start;
points=[];


function ajax_loading(element)
{
    var t=$(element) ;
    var offset = t.offset();
                var dim = {
                    left:    offset.left,
                    top:    offset.top,
                    width:    t.outerWidth(),
                    height:    t.outerHeight()
                };
    $('<div class="ajax_loading"></div>').css({
                    position:    'absolute',
                    left:        dim.left + 'px',
                    top:        dim.top + 'px',
                    width:        dim.width + 'px',
                    height:        dim.height + 'px'
                }).appendTo(document.body).show();

}

//function to create label
function Label(point, html, classname, pixelOffset) {
    // Mandatory parameters
    this.point = point;
    this.html = html;

    // Optional parameters
    this.classname = classname || "";
    this.pixelOffset = pixelOffset || new GSize(0, 0);
    this.prototype = new GOverlay();

    this.initialize = function(map) {
        // Creates the DIV representing the label
        var div = document.createElement("div");
        div.style.position = "absolute";
        div.innerHTML = '<div class="' + this.classname + '">' + this.html + '</div>';
        div.style.cursor = 'pointer';
        div.style.zindex = 12345;
        map.getPane(G_MAP_MAP_PANE).parentNode.appendChild(div);
        this.map_ = map;
        this.div_ = div;
    }
// Remove the label DIV from the map pane
    this.remove = function() {
        this.div_.parentNode.removeChild(this.div_);
    }
// Copy the label data to a new instance
    this.copy = function() {
        return new Label(this.point, this.html, this.classname, this.pixelOffset);
    }
// Redraw based on the current projection and zoom level
    this.redraw = function(force) {
        if (!force) return;
        var p = this.map_.fromLatLngToDivPixel(this.point);
        var h = parseInt(this.div_.clientHeight);
        this.div_.style.left = (p.x + this.pixelOffset.width) + "px";
        this.div_.style.top = (p.y + this.pixelOffset.height - h) + "px";
    }
}

//add graph to point
function addGraph(url) {
     ajax_loading('#map');

    maxLon= map.getBounds().getNorthEast().lat();
    maxLat=map.getBounds().getNorthEast().lng();
    minLon=map.getBounds().getSouthWest().lat();
    minLat=map.getBounds().getSouthWest().lng();
    zoom=map.getZoom();

    var URL=url+ "?maxLat="+ maxLat + "&maxLon=" +maxLon +"&minLat="+ minLat + "&minLon=" + minLon +"&zoom=" + zoom+"&start="+slider_start_ts+"&end="+slider_end_ts;
    
    $.ajax({
            type: "GET",
            url: URL,
            dataType: "json",
            success: function(data){
         $.each(data, function(key, value){

    var start = new google.maps.LatLng(parseFloat(value['lon']), parseFloat(value['lat']));
   
    // Add a Circle overlay to the map.
        var circle = new google.maps.Circle({
          center:start,
          map: map,
          strokeColor:value['color'],
          radius:30000*parseFloat(value['heat']), // 3000 km
          fillColor:value['color'],
           strokeWeight: 1
        });
             if (layers[url])
             {
                 layers[url].push(circle);
             }
             else{
                 layers[url]=[];
                    layers[url].push(circle);

             }





       descriptions[start][url]="<p>"+value['desc']+"</p>";

       circle.bindTo('position', markers[start]);
    
            });},
        complete:function(status){

          $('.ajax_loading').remove();
        }
        
    });

}

function removeGraph(url)
{
         for (i=0;i<layers[url].length;i++)
         {

        layers[url][i].setMap(null);
         }
    layers[url]=null;

    for (p=0;p<points.length;p++)
    {
        descriptions[points[p]][url]='';
    }



}
/*
 * add a markers given the  the marker data url
 *
 */
function addMarkers(url) {


    $.ajax({
            type: "GET",
            url: url,
            dataType: "json",
            success: function(data){
         $.each(data, function(key, value){
             var point = new google.maps.LatLng(parseFloat(value['lon']),parseFloat(value['lat']));


            var mIcon  = new google.maps.MarkerImage(value['icon'],new google.maps.Size(20, 20));
            mIcon.iconAnchor = new google.maps.LatLng(10, 10);

             var marker = new google.maps.Marker({
                   position: point,
                   map: map,
                   icon: value['icon'],
                   title:value['title']
               });
             if(!descriptions[point])
                         {
                         descriptions[point]={};
                         descriptions[point][url]="<p class='help'>"+value['title']+"</p>";

                         }
             marker.setIcon(mIcon);
             markers[point]=marker;
             points.push(point);
             google.maps.event.addListener(marker, 'click', function() {
                 var desc="";
                  $.each(descriptions[point], function(key, value){

                    desc=desc+value;
                     
                 });
             new google.maps.InfoWindow({content:desc

           }).open(map,marker);
                });

             marker.setMap(map);

         });
                  }

        });


	

}


//    function to draw simple map
function init_map() {

     //make sure the zoom fits all the points

    var myOptions = {
          mapTypeId: google.maps.MapTypeId.ROADMAP
        };
        map = new google.maps.Map(document.getElementById("map"),
            myOptions);
    var bounds = new google.maps.LatLngBounds()
    bounds.extend(new google.maps.LatLng(parseFloat(minLon), parseFloat(minLat)));
    bounds.extend(new google.maps.LatLng(parseFloat(maxLon), parseFloat(maxLat)));
    map.fitBounds(bounds);


}


function toggle_select(elem,url){
    if($(elem).attr("checked"))
    {
        if(layers[url])
        {
        removeGraph(url);
        $(elem).attr('checked', false);
        }
        else{
           addGraph(url);
        }


            }
        else{
        if(layers[url])
        {
        removeGraph(url);
         $(elem).attr('checked', false);
        }
        else{
            addGraph(url);
             $(elem).attr('checked', true);

        }


    }

}

//add layer placeholders
//iterate the layer list and add it to the layer container
function add_layers(map_layers)
{
     var layerContainer = $('#overlays');//dom element containing layers
        $.each( map_layers, function( key, val ) {

        	var color=val[2];
            //console.log(color);
            //var color='#ff0000';

            layerContainer.append('<li><input type="checkbox"   onchange="toggle_select(this,\''+val[1]+'\')"   ></input><a url ="'+val[1]+'" href="javascript:void(0)" onclick="toggle_select($(this).prev(),\''+val[1]+'\')" >'+val[0]+'</a><span style="width:15px;height:15px;background-color:'+color+';float:right;margin-top:3px;margin-right:6px;"></span></li>');
        });


}


//fetch url content

function fetchContent(url){
    
    $.ajax({
        type: "GET",
        url: url,
        dataType: "json",
        success: function(data){
            return data;
            
        }

    });


}

function filter_by_date()
{

    $('#overlays').find('input:checked').each(function (){

        var url=String($(this).next().attr('url'));
        removeGraph(url);
        addGraph(url);

    });

}

$(document).ready(function() {

            init_map();
            addMarkers(base_layer);

});