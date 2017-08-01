$(document).ready(function() {
	var props = load_node_props("data/ising_spin_16_2.xml");
	load_property_menu(props);
	var data, events;

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
    	
	  	d3.selectAll("svg").remove();
	  	// slowing down?
		data = load_graph_instance("data/ising_spin_16_2.xml");
		load_initial_graph_state("data/ising_spin_16_2_event.xml", data);

		events = load_graph_events("data/ising_spin_16_2_event.xml");

		data.events = events;

		sessionStorage.setItem("data", JSON.stringify(data));
		graph = new SubGraph("body", data);
		graph.change_active_node("n_6_6");
		graph.create_adjacency_list();
		graph.create_subgraph();
		graph.draw();
    }
});