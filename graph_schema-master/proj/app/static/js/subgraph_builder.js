function SubGraph(selector, data) {
	// d3 vars
	var width = window.innerWidth * 0.7;
   	var height = window.innerHeight * 0.98;
  	var _data = data;
  	var active_node = init_active_node();
  	var subgraph = {"nodes": {}, "edges": []};
  	var adj = {};
    
    
  // logic vars
  var simulating = false;
    var prop_domain = [Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY];
    var message_passing_time = 100;
    var symbol_size = 300;
    var last_event_time = get_last_event_time();
  	var max_depth = 4;

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
				g.attr("transform", d3.event.transform);
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
                    .force("link", d3.forceLink().id(function(d) { return d.id; }).distance(50).strength(0.1))
                    .force("charge", d3.forceManyBody())
                    .force("center", d3.forceCenter(width / 2, height / 2));

        link = g.append("g")
                        .attr("class", "edges")
                        .selectAll("line")
                        .data(subgraph.edges)
                        .enter().append("line")
                        .attr("stroke", "#cccccc")
                        .attr("class", function(d) { edge_class(d)});

        node = g.append("g")
                    .attr("class", "nodes")
                    .selectAll(".device")
                    .data(d3.values(subgraph.nodes))
                    .enter().append("path")
                    .attr("class", function(d) { return "device " + d.id + " " + border_node_class(d)})
                    .attr("d", d3.symbol().size( function(d) {if (d.id == active_node) {
                        return 500
                      } else {
                        return 300;
                      }
                    }).type(d3.symbolCircle))
                    .attr("fill", "#000000")
                    .attr("stroke", function(d) { 
                      if (d.id == active_node) {
                        return "red"
                      } else {

                          var selected = $("input[name='property']:checked").val();

                          if (typeof(selected) != 'undefined') {
                            return get_node_colour(selected, d.p[selected])
                          }

                          return "#FFFFFF";
                        }
                    })
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
                        show_device_details(d);
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

        simulation.nodes(d3.values(subgraph.nodes))
                    .on("tick", ticked);

        simulation.force("link")
                    .links(subgraph.edges);

        function border_node_class(node) {
          if (node.depth == max_depth) {
            return "border-node";
          } else if (node.depth == max_depth - 1) {
            return "subborder-node";
          } else {
            return "";
          }
        }

        function edge_class(edge) {
          return edge.source  + ":" + edge.target;
        }

        function ticked() {
          // TODO: incorporate radial depth somehow
            link
                .attr("x1", function(d) { return link_x(d.source); })
                .attr("y1", function(d) { return link_y(d.source); })
                .attr("x2", function(d) { return link_x(d.target); })
                .attr("y2", function(d) { return link_y(d.target); });

            node.attr("transform", function (d) {
                if (d.id == active_node) { 
                    if (d.x == width/2 && d.y == height/2) {
                      return "translate(0, 0)"
                    } else {
                      return "translate(" + width/2 + ", " + height/2 + ")"
                    }
                } else { return "translate(" + d.x + ", " + d.y + ")";}
            });
        }

        function link_x(node) {
          if (node.id == active_node) {
            return width / 2;
          } else {
            return node.x;
          }
        }

        function link_y(node) {
          if (node.id == active_node) {
            return height / 2;
          } else {
            return node.y;
          }
        }

        function show_device_details(d) {
            $.get({
                   url: '/device_details', 
                   success: function(response) {
                        sessionStorage.setItem('active_device', d.id);
                        window.location.href = '/device_details';

                   }
            });

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

    this.create_subgraph = function() {
        var depth = max_depth;

        // TODO: helper queue class because O(N)
        // TODO: change bfs to more efficient?
        var q = [];
        q.push(active_node);

        var nodes = {};

        var curr_depth = 0,
            remaining_nodes_at_curr = 1,
            next_remaining = 0;

        while (q.length != 0) {
            var curr = q.shift();
            
            if (!(curr in nodes)) {
              nodes[curr] = curr_depth;
            }

            next_remaining += adj[curr].size;

            if ((remaining_nodes_at_curr -= 1) == 0) {
                if ((curr_depth += 1) > depth) { break; };
                remaining_nodes_at_curr = next_remaining;
                next_remaining = 0;
            }

            q = q.concat(Array.from(adj[curr]));
        }

        var i = 0;
        for (var node in nodes) {
          subgraph.nodes[node] = data.nodes[node];
          subgraph.nodes[node].depth = nodes[node];
        }

        for (var node in subgraph.nodes) {
          subgraph.edges = subgraph.edges.concat(find_edges_within_subgraph(data.edges, node, nodes));
        }

        // TODO: only send events
        var events = [];

        for (var i = 0; i < data.events.send.length; i++) {
          if (data.events.send[i].dev in subgraph.nodes) {
            events.push(data.events[i]);
          }
        }

        subgraph.events = events;
    }


   	this.change_active_node = function(new_node) {
   		// called on new node double click
   		active_node = new_node;
   	}


    function init_active_node() {
        // rank each node through num edges
        // return max edges
    }

   	this.create_adjacency_list = function() {
        // TODO: unconnected nodes
   		for (var i = 0; i < data.edges.length; i++) {
   			var node = adj[data.edges[i].source];

   			if (typeof(node) == 'undefined') {
   				adj[data.edges[i].source] = new Set();
   			}

   			adj[data.edges[i].source].add(data.edges[i].target);
   		}// TODO: http://staff.vbi.vt.edu/maleq/papers/conversion.pdf 
   	}


  function get_last_event_time() {
    var sends = data.events.send;
    var recvs = data.events.recv;

    return Math.max(sends[sends.length - 1], recvs[recvs.length - 1]);
  }

  function get_node_colour(prop, value) {
    var colour = d3.scaleLinear()
              .domain(prop_domain)
              .interpolate(d3.interpolateHcl)
                .range([d3.rgb("#007AFF"), d3.rgb('#FF0000')]);

        return colour(value);
  }



}


function find_edges_within_subgraph(edges, source_id, nodes) {
    var edgeList = []
    for (var i = 0; i < edges.length; i++) {
        if (edges[i].source == source_id && edges[i].target in nodes) {
                edgeList.push(edges[i]);
        }
    }

    return edgeList;
}

