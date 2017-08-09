$(document).ready(function() {
	
	reset_graph()

	$('input[type="radio"]').click(function(){
	    if ($(this).is(':checked')) {
	    	if (graph.simulating) {
	    		graph.stop_poets_simulation();
	    	}
	    	graph.change_colour(this.value);
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
    	$(':radio').prop('checked', false);

        if (typeof(graph) != "undefined") {
        	graph.stop_poets_simulation();
	  	}

	  	d3.selectAll("svg").remove();
		data.events = [];


		graph = new ForceGraph("body", data, level);
		graph.draw();
    }
});