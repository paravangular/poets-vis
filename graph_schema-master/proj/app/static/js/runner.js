$(document).ready(function() {
	load_property_selector()
	reset_graph()

	snap = new Stepper(parent_id, max_level);
	snapshots = snap.get_snapshots();


	if (level == max_level - 1) {
		graph.calculate_messages();
	}

	var neighbours = new Set()
	for (var id in data.nodes) {
		var ls = id.split("_")
		if (ls[0] == "base" && ls.length == level + 1) {
			neighbours.add(id)
		}
	}

	for (let p of neighbours) {
		console.log(p)
		$.ajax({
		    url: "/preload_partition",
		    type: "GET",
		    data: {
				part_id: p 
			},
		    success: function (d) {
		    	console.log("Success preloading neighbours to cache.")
		    },
		    error: function () {
		        console.log('Error obtaining neighbour data');
		    }
		});
	}


	$('input[type="radio"]').click(function(){
	    if ($(this).is(':checked')) {
	    	if (graph.simulating) {
	    		graph.stop_poets_simulation();
	    	}
	    	graph.clear();
	    	graph.draw();
	    }
	});

	$("#stop").addClass('disabled'); 
	$("#pause").addClass('disabled'); 
    
    $("#start").click(function(){
        graph.start_poets_simulation();
    });

    $("#stop").click(function(){
        graph.stop_poets_simulation();

    }); 

    $("#pause").click(function(){
        graph.pause_poets_simulation();

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
	count = {};

	if (level == max_level - 1) {
		$('<input type="radio" name="property" id="messages_sent_radio" value= "messages_sent" checked="checked"><label for="messages_sent_radio">messages sent</label><br>').appendTo("#property-menu");
		$('<input type="radio" name="property" id="messages_received_radio" value= "messages_received"><label for="messages_received_radio">messages received</label><br>').appendTo("#property-menu");
	}
	for (var state in prop_domains) {
		if (state != "messages_received" && state != "messages_sent") {
			$('<input type="radio" name="property" id= "' + state + '_radio" value= "' + state + '"><label for="' + state + '_radio">' + state + '</label><br>').appendTo("#property-menu");
		}
	}

	if (level != max_level - 1) {
	    $('input[type=radio][name=property]:first').attr('checked', true);
	}
}