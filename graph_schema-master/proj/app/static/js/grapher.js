var SYMBOLS = [d3.symbolCircle, d3.symbolSquare, d3.symbolTriangle, d3.symbolDiamond, d3.symbolCross, d3.symbolStar, d3.symbolWye];

function ForceGraph(selector, data, level) {

  	// d3 vars
	var width = window.innerWidth * 0.7;
   	var height = window.innerHeight * 0.8;
  	var _data = data;

  	var simulating = false;
  	var symbol_size = 300;
  	var prop_domains = {}
  	var types = {}

  	var key;
  	for (var k in data.nodes) {
  		key = k;
  		break;
  	}

  	for (var prop in _data.nodes[key]) {
  		prop_domains[prop] = [Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY]
  	}

  	var si = 0
  	for (var node in _data.nodes) {
  		if (_data.nodes[node]["type"] && !(_data.nodes[node]["type"] in device_types)) { 
  			device_types[_data.nodes[node]["type"]] = SYMBOLS[si];
  			si++;
  		}

  		for (var prop in prop_domains) {
  			var n = _data.nodes[node][prop]
  			if (!isNaN(parseFloat(n)) && isFinite(n)) {
  				prop_domains[prop][0] = Math.min(Number(n), prop_domains[prop][0])
  				prop_domains[prop][1] = Math.max(Number(n), prop_domains[prop][1])
  			}

  		}
  	}


  	svg = d3.select("body")
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
   		var simulation = d3.forceSimulation()
				    .force("link", d3.forceLink().id(function(d) { return d.id; }).distance(80).strength(0.15))
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
				    	if (d.type) {return device_types[d.type]}
				    	else {return d3.symbolCircle} } ))
				    .attr("fill", function(d) { 
				    	var selected = $("input[name='property']:checked").val();
				    	var selected = "spin"
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

	this.stop_poets_simulation = function() {
		simulating = false;
		d3.selectAll("circle.marker").remove();

        $("#stop").prop('disabled', true);
        $("#start").prop('disabled', false);
	}
	   	
	this.start_poets_simulation = function() {

        $("#start").prop('disabled', true);
        $("#stop").prop('disabled', false);
		simulating = true;

		var range = $('#slider').slider("option", "values");
		var animator = new Animator(this, g, parseFloat(range[0]), parseFloat(range[1]), parent_id);

	}

	this.update_nodes = function(device, evt) {
		val = JSON.parse(evt.s)
		for (var prop in val) {
			data.nodes[device][prop] = val[prop]
		}

		var node = d3.select("." + device);

		node.attr("fill", function(d) { 
			return get_node_colour("spin", data.nodes[device]["spin"]);
		});
	}

	function get_node_shape(dev_type) {
		d3.symbolCircle
	}

	function get_node_size(id) {
		var ls = id.split("_")
		if (ls[0] == "base" && ls.length == level + 1) {
			return symbol_size * 7
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
  						.domain(prop_domains[prop])
  						.interpolate(d3.interpolateHcl)
      					.range([d3.rgb("#007AFF"), d3.rgb('#FF0000')]);

      	return colour(value);
   	}

}


function find_edges_by_source_id(edges, source_id) {
	var edgeList = []
	for (var i = 0; i < edges.length; i++) {
   		if (edges[i].source === source_id) {
     			edgeList.push(edges[i]);
   		}
  	}

  	return edgeList;
}

function get_last_child(xmln) {
    var x = xmln.lastChild;
    while (x.nodeType != 1) {
        x = x.previousSibling;
    }
    return x;
}


