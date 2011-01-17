var colors=[];
var points=[];
var base_url;

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
function addGraph(data, x, y, color, desc) {
    //get map width and height in lat lon
    var d = map.getBounds().toSpan();
    var height = d.lng();
    var width = d.lat();
    var maxsize = 0.9;
    var pointpair = [];
    var increment = (parseFloat(height) / 10.0) / 100;
    var start = new GPoint(parseFloat(x), parseFloat(y));
    var volume = parseInt((parseFloat(data) * 100) / maxsize);

    pointpair.push(start);
    //draw the graph as an overlay
    pointpair.push(new GPoint(parseFloat(x + increment), parseFloat(y + increment)));
    var line = new GPolyline(pointpair, color, volume);

    map.addOverlay(line);
}

/*
 * add a marker given the lat,lon,title icon and the data url
 *
 * the data urls is to identify markers belonging to a particular overlay
 */
function addMarker(x,y,title,icon,url) {


		var point = new GPoint(parseFloat(x),parseFloat(y));
		var mIcon  = new GIcon(G_DEFAULT_ICON, icon);

		mIcon.iconSize = new GSize(20,20);
		mIcon.shadowSize=new GSize(0,0);
		mIcon.iconAnchor = new GPoint(10, 10);
		var marker = new GMarker(point,mIcon);
		map.addOverlay(marker);
		var desc=[];



		var ev=GEvent.addListener(marker, 'click',
				function() {
					//convert the disc list to a string and display in window
			marker.openInfoWindowHtml('<p class="help">'+title+'</h1>'+'<p>'+String(desc).replace(",","")+'</p>');
		});


	

}


//    function to draw simple map
function init_map() {

    //initialise the map object
    map = new GMap2(document.getElementById("map"));
    //add map controls
    map.addControl(new GLargeMapControl());
    map.addControl(new GMapTypeControl());

    //make sure the zoom fits all the points
    var bounds = new GLatLngBounds;
    bounds.extend(new GLatLng(parseFloat(minLon), parseFloat(minLat)));
    bounds.extend(new GLatLng(parseFloat(maxLon), parseFloat(maxLat)));
    map.setCenter(bounds.getCenter(), map.getBoundsZoomLevel(bounds));

    GEvent.addListener(map,'zoomend',function() {
        //load_layers(map_poll_pk)
    });

}

function toggle_select(elem){
    console.log(elem);
    if($(elem).attr("checked"))
    {
    $(elem).attr('checked', false);
            }
        else{
         $(elem).attr('checked', true);

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

            layerContainer.append('<li><input type="checkbox"  onchange="addGraph("'+map_layers[key][1]+'")"></input><a href="javascript:void(0)" onclick="toggle_select($(this).prev()),addGraph(map_layers[\''+key+'\'][1])" >'+val[0]+'</a><span style="width:15px;height:15px;background-color:'+color+';float:right;margin-top:3px;margin-right:6px;"></span></li>')});


}


//fetch url content

function fetchContent(url){
    $.ajax({
        type: "GET",
        url: url,
        dataType: "json",
        success: function(data){
            $.each(data, function(key, value){


                  
                    addMarker(value['lat'],value['lon'],value['title'],value['icon']);

               
          

            });



        }

    });

}



$(document).ready(function() {

            init_map();
            fetchContent(base_layer);

});