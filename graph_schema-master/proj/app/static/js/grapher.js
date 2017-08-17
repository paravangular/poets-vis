var SYMBOLS = [d3.symbolCircle, d3.symbolSquare, d3.symbolTriangle, d3.symbolDiamond, d3.symbolCross, d3.symbolStar, d3.symbolWye];
var port_colors = d3.scaleLinear().domain([0, Object.keys(ports).length])
      .interpolate(d3.interpolateHcl)
      .range([d3.rgb("#007AFF"), d3.rgb('#FFF500')]);


var i = 0;
for (var port in ports) {
	ports[port] = port_colors(i)
	i++;
}

var message_type_colors = d3.scaleLinear().domain([0, Object.keys(message_types).length])
      .interpolate(d3.interpolateHcl)
      .range([d3.rgb("#007AFF"), d3.rgb('#FFF500')]);

var i = 0;
for (var msg in message_types) {
	message_types[msg] = port_colors(i)
	i++;
}

function ForceGraph(selector, data, level) {

  	// d3 vars
	var width = window.innerWidth * 0.6;
   	var height = document.documentElement.clientHeight;
  	var _data = data;

  	var simulating = false;
  	var symbol_size = 300;
  	var selected = $("input[name='property']:checked").val();

  	var animator;
  	var key;
  	for (var k in data.nodes) {
  		key = k;
  		break;
  	}

  	var si = 0
  	for (var dev in device_types) {
  		device_types[dev]["shape"] = SYMBOLS[si];
  		si++
  	}

  	svg = d3.select("#viewport")
      	.append("svg")
		.attr("width", width)
		.attr("height", height);
	
	svg.append("rect")
	    .attr("width", width)
	    .attr("height", height)
	    .style("fill", "none")
	    .style("pointer-events", "all")
	    .call(d3.zoom()
	    	.on("zoom", function() {
				if (!simulating) {
			    	g.attr("transform", d3.event.transform);
			    }
			}));

	var g = svg.append("g");

	var tooltip = d3.select("body").append("div").attr("class", "tooltip");


    this.data = function(value) {
    	if(!arguments.length) {
        	return _data;
      	}
      	
      	_data = value;
      	return this;
   	}

   	this.draw = function() {
   		selected = $("input[name='property']:checked").val();
   		var sequential_scale = d3.scaleSequential(d3.interpolateHcl(d3.rgb("#007AFF"), d3.rgb('#FF0000')))
  				.domain([prop_domains[selected].min, prop_domains[selected].max]); 				;

  		svg.append("g")
		  .attr("class", "legend")
		  .attr("transform", "translate(20,20)");

		var legend = d3.legendColor()
		    .shapeWidth(30)
		    .cells(10)
		    .orient("vertical")
		    .scale(sequential_scale)

		svg.select(".legend")
  			.call(legend);

   		var simulation = d3.forceSimulation()
				    .force("link", d3.forceLink().id(function(d) { return d.id; }).distance(function(d) { return 100 }).strength(0.15))
				    .force("charge", d3.forceManyBody())
				    .force("center", d3.forceCenter(width / 2, height / 2));

		link = g.append("g")
				    	.attr("class", "edges")
				    	.selectAll("line")
				    	.data(_data.edges)
				    	.enter().append("line")
						.attr("stroke", "#cccccc")
						.attr("class", function(d) { return d.source + ":" + d.target });

		node = g.append("g")
				    .attr("class", "nodes")
				    .selectAll(".device") // TODO: device shape
				    .data(d3.values(d3.values(_data.nodes)))
				    .enter().append("path")
				    .attr("class", function(d) { return "device " + d.id })
				    .attr("d", d3.symbol().size( function(d) { return get_node_size(d.id) } ).type(function(d) { 
				    	if (d.type) {return device_types[d.type]["shape"]}
				    	else {return d3.symbolCircle} } ))
				    .attr("fill", function(d) { 
				    	return get_node_colour(selected, d[selected])
				    })
				    .attr("opacity", function(d) {
				    	return get_node_opacity(d.id)
				    })
				    .attr("stroke", "#FFFFFF")
				    .attr("stroke-width", "2px")
				    .on("click", function(d) { 
				    	tooltip
			              .style("display", "inline-block")
			              .html(show_node_state(d));

			            var tooltip_node = d3.select('.tooltip')._groups[0][0];

			            var tooltip_width =  tooltip_node.getBoundingClientRect().width;
			            var tooltip_height = tooltip_node.getBoundingClientRect().height;

			            tooltip.style("left", d3.event.pageX - tooltip_width / 2 + "px")
			              	.style("top", d3.event.pageY - (tooltip_height + 20) + "px")

				    	if (d3.select(this).classed("selected-node")) {
				    		d3.select(this)
								.classed("selected-node", false);

				    	} else {
				    		d3.select(".selected-node")
								.classed("selected-node", false);

							d3.select(this)
								.classed("selected-node", true);
				    	}
					})
				    .on("dblclick", function(d) {
				    	show_details(d);
				    })
				    .on("mouseout", function(d) {
				    	tooltip
				    		.style("display", "none");

				    	if (d3.select(this).classed("selected-node")) {
				    		d3.select(this)
								.classed("selected-node", false);

				    	}
				    })
				    .call(d3.drag()
			        .on("start", dragstarted)
			        .on("drag", dragged)
			        .on("end", dragended));

		simulation.nodes(d3.values(_data.nodes))
	      			.on("tick", ticked);

	  	simulation.force("link")
	      			.links(_data.edges);

	    function ticked() {
			link
		        .attr("x1", function(d) { return d.source.x; })
		        .attr("y1", function(d) { return d.source.y; })
		        .attr("x2", function(d) { return d.target.x; })
		        .attr("y2", function(d) { return d.target.y; });

		    node.attr("transform", function (d) {return "translate(" + d.x + ", " + d.y + ")";});
		}

		function show_details(d) {

			if (d.id.split("_")[0] == "base") {
				$.get({
				       url: '/graph/' + d.id, 
				       success: function(response) {
					        window.location.href = '/graph/' + d.id;
					        parent_id = d.id;

				       }
				});
			} else {
				$.get({
					url: '/device/' + d.id,
					success: function(response) {
						window.location.href = '/device/' + d.id;
					}
				})
			}

		}

		function show_node_state(d) {
			var prop_string = 'ID: ' + d.id + '<br>' + 'Type: ' + d.type + '<br>';

			for (var prop in d.p) {
				prop_string += prop + ': ' + d.p[prop] + '<br>';
			}

			return prop_string;
		}

		function dragstarted(d) {
			if (!simulating) {
				if (!d3.event.active) simulation.alphaTarget(0.3).restart();
			    d.fx = d.x;
			    d.fy = d.y;
			}
		    
		  }

		  function dragged(d) {
			if (!simulating) {
			    d.fx = d3.event.x;
			    d.fy = d3.event.y;
			}
		  }

		  function dragended(d) {
			if (!simulating) {
				 if (!d3.event.active) simulation.alphaTarget(0);
			    d.fx = null;
			    d.fy = null;
			}
		   
		  }
   	}

	this.clear = function() {
   		d3.selectAll("g > *").remove();
   	}

	this.pause_poets_simulation = function() {
		simulating = false;

		animator.stop_animation();
		d3.selectAll("circle.message").transition();


        $("#pause").addClass('disabled'); 
        $("#stop").removeClass('disabled'); 
        $("#start").removeClass('disabled'); 
	}

	this.stop_poets_simulation = function() {
		simulating = false;

		animator.stop_animation();
		d3.selectAll("circle.message").remove();


        $("#pause").addClass('disabled'); 
        $("#stop").addClass('disabled'); 
        $("#start").removeClass('disabled'); 
	}
	   	
	this.start_poets_simulation = function() {


        $("#pause").removeClass('disabled'); 
        $("#start").addClass('disabled'); 
        $("#stop").removeClass('disabled'); 
		simulating = true;

		var range = $('#slider').slider("option", "values");
		if (level == max_level - 1) {
			animator = new EventAnimator(this, g, parseFloat(range[0]), parseFloat(range[1]), parent_id);
		} else {
			animator = new SnapshotAnimator(this, g, parseFloat(range[0]), parseFloat(range[1]), parent_id);
		}

		

	}

	this.update_parts = function(part, new_state) {
		for (var prop in new_state) {
			if (prop in data.nodes[part]) {
				data.nodes[part][prop] = new_state[prop]
			}
		}

		var node = d3.select("." + part);

		selected = $("input[name='property']:checked").val();
		node.attr("fill", function(d) { 
			return get_node_colour(selected, data.nodes[part][selected]);
		});

	}

	this.update_nodes = function(device, evt, evt_type) {
		val = JSON.parse(evt.s)
		for (var prop in val) {
			data.nodes[device][prop] = val[prop]
		}

		if (evt_type == "send") {
			data.nodes[device]["messages_sent"] += 1
		} else if (evt_type == "recv") {
			data.nodes[device]["messages_received"] += 1
		} 

		var node = d3.select("." + device);

		selected = $("input[name='property']:checked").val();
		node.attr("fill", function(d) { 
			return get_node_colour(selected, data.nodes[device][selected]);
		});
	}

	function get_node_shape(dev_type) {
		d3.symbolCircle
	}

	function get_node_size(id) {
		var ls = id.split("_")
		if (ls[0] == "base" && ls.length >= level + 1) {
			return (20 * symbol_size) / (ls.length) 
		} else {
			return symbol_size
		}
	}

	function get_node_opacity(id) {
		var ls = id.split("_")
		if (ls[0] == "base" && ls.length == level + 1) {
			return 0.3
		} else {
			return 1
		}
	}

	function get_node_colour(prop, value) {
		var colour = d3.scaleLinear()
  						.domain([prop_domains[prop].min, prop_domains[prop].max])
  						.interpolate(d3.interpolateHcl)
      					.range([d3.rgb("#007AFF"), d3.rgb('#FF0000')]);

      	return colour(value);
   	}


}


