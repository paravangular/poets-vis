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
	var text = svg.append("text")
			.attr("class", "epoch-text")
			.text("0")
			.attr("transform", "translate(" + (width - 20) + ", 20)")
			.attr("font-size", "3em")
			.attr("text-anchor", "end")
			.attr("alignment-baseline", "hanging")

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
			}
		}

		function show_node_state(d) {
			var prop_string = '<table class="fb"><tr><td>ID:</td> <td> ' + d.id + '</td></tr>'
			if (d.type != null) { prop_string += '<tr><td>type: </td> <td>' + d.type + '</td></tr>'; } else { prop_string += '<td>type:</td> <td>partition</td></tr>';}
			
			for (var prop in d) {
				if (d.type == null && (prop == "messages_sent" || prop == "messages_received")) {
					continue;
				}
				
				if (prop in prop_domains && d[prop] != null) {
					prop_string += '<tr><td>' + prop + ':</td> <td>' + d[prop] + '</td></tr>';
				}
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

		pause_time = d3.select(".epoch-text").text()

        for (dev in snapshots[pause_time]) {
            graph.update_snapshot(dev, snapshots[pause_time][dev])
        }

        $("#pause").addClass('disabled'); 
        $("#stop").removeClass('disabled'); 
        $("#start").removeClass('disabled'); 
	}

	this.stop_poets_simulation = function() {
		simulating = false;

		animator.stop_animation();
		d3.selectAll("circle.message").remove();
        for (dev in snapshots[0]) {
            graph.update_snapshot(dev, snapshots[0][dev])
        }

        $("#pause").addClass('disabled'); 
        $("#stop").addClass('disabled'); 
        $("#start").removeClass('disabled'); 
	}
	   	
	this.start_poets_simulation = function() {


        $("#pause").removeClass('disabled'); 
        $("#start").addClass('disabled'); 
        $("#stop").removeClass('disabled'); 
		simulating = true;

		var range = $('#event-slider').slider("option", "values");
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

	this.update_snapshot = function(device, snapshot) {
		for (var prop in snapshot) {
			if (prop in data.nodes[device]) {
				data.nodes[device][prop] = snapshot[prop]
			}
		}

		var node = d3.select("." + device);

		selected = $("input[name='property']:checked").val();
		node.attr("fill", function(d) { 
			return get_node_colour(selected, data.nodes[device][selected]);
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

	this.calculate_messages = function() {
		$.ajax({
		    url: "/events",
		    type: "GET",
		    dataType: 'json',
		    data: { 
		    	start: 0,
				end: max_time,
				part_id: parent_id 
			},
		    success: function (d) {
		    	events = d;
		    	update_messages(events)
		    },
		    error: function () {
		        alert('Error obtaining event data for partition ' + parent_id + ' in range ' + 0 + ' to ' + max_time + '.');
		    }
		});

		function sort_send(a, b) {
		  if (a.time < b.time)
		    return -1;
		  if (a.time > b.time)
		    return 1;
		  return 0;
		}

		function update_messages(events) {
			var sent_so_far = {}
			events.send.sort(sort_send)

			for (var i = 0; i < events.send.length; i++) {
				if (events.send[i].dev in sent_so_far) {

					for (var t = sent_so_far[events.send[i].dev][1]; t < events.send[i].time; t++) {
						if (t in snapshots) {
							snapshots[t][events.send[i].dev]["messages_sent"] = sent_so_far[events.send[i].dev][0]
						}
					}
					snapshots[events.send[i].time][events.send[i].dev]["messages_sent"] = sent_so_far[events.send[i].dev][0] + 1;
					sent_so_far[events.send[i].dev][0]++
					sent_so_far[events.send[i].dev][1] = events.send[i].time
				} else {
					snapshots[events.send[i].time][events.send[i].dev]["messages_sent"] = 1
					sent_so_far[events.send[i].dev] = [1, events.send[i].time]
				}
				
			}

			for (dev in sent_so_far) {
				var t = sent_so_far[dev][1]
				var e = sent_so_far[dev][0]

				var s = max_time
				while (t <= max_time) {
					snapshots[t][dev] = e;
					t++;
				}
			}
			
			var recv_so_far = {}
			var recv = Object.values(events.recv);
			recv.sort(sort_send)

			for (var i = 0; i < recv.length; i++) {
				if (recv[i].dev in recv_so_far) {

					for (var t = recv_so_far[recv[i].dev][1]; t < recv[i].time; t++) {
						if (t in snapshots) {
							snapshots[t][recv[i].dev]["messages_received"] = recv_so_far[recv[i].dev][0]
						}
					}
					snapshots[recv[i].time][recv[i].dev]["messages_received"] = recv_so_far[recv[i].dev][0] + 1;
					recv_so_far[recv[i].dev][0]++
					recv_so_far[recv[i].dev][1] = recv[i].time
				} else {
					snapshots[recv[i].time][recv[i].dev]["messages_received"] = 1
					recv_so_far[recv[i].dev] = [1, recv[i].time]
				}
				
			}

			for (dev in recv_so_far) {
				var t = recv_so_far[dev][1]
				var e = recv_so_far[dev][0]

				var s = max_time
				while (t <= max_time) {
					snapshots[t][dev] = e;
					t++;
				}
			}
		}
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


