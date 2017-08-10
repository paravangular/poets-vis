$(document).ready(function() {
	load_property_selector()
	reset_graph()

	$('input[type="radio"]').click(function(){
	    if ($(this).is(':checked')) {
	    	if (graph.simulating) {
	    		graph.stop_poets_simulation();
	    	}
	    	graph.clear();
	    	graph.draw();
	    }
	});

	$("#stop").prop('disabled', true);
    
    $("#start").click(function(){
        graph.start_poets_simulation();
    });

    $("#stop").click(function(){
        graph.stop_poets_simulation();

    }); 

    $("#reset").click(function(){
        window.top.location = window.top.location;
    });


    function reset_graph() {

        if (typeof(graph) != "undefined") {
        	graph.stop_poets_simulation();
	  	}

	  	d3.selectAll("svg").remove();
		data.events = [];


		graph = new ForceGraph("body", data, level);
		graph.draw();
    }
});


function load_property_selector() {
	$('<div>States and Properties</div>').appendTo('#property-menu');

	for (var dev in device_types) {
		var title = "Device type: " + dev;
		$('<div>' + title + '</div>').appendTo('#property-menu');

		$('<input type="radio" name="property" value= "messages_sent" checked="checked">messages sent<br>').appendTo("#property-menu");
		$('<input type="radio" name="property" value= "messages_received">messages received<br>').appendTo("#property-menu");

		var states = device_types[dev]["states"].split(",")

		for (var i = 0; i < states.length; i++) {
			if (states[i][0] != "[" && states[i][states[i].length - 1] != "]") {
				$('<input type="radio" name="property" value= "' + states[i] + '">' + states[i] + '<br>').appendTo("#property-menu");
			}
		}
	}

}