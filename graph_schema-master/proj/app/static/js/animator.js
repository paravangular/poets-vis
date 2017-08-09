function Message(graph, g, send_event, recv_event) {
	var source_device = send_event.dev,
		source_port = send_event.port,
		target_device = recv_event.dev,
		target_port = recv_event.port,
		event_duration = Math.max(1000, (recv_event.time - send_event.time) * 100) // default

	/*
	event time
	start location - end location
	*/

	var edge_class = "." + source_device + "\\:" + target_device;


	this.draw = function() {

		var path = d3.select(edge_class)
		if (path) {
			var src = get_node_centroid(source_device);
			var dest = get_node_centroid(target_device);
			graph.update_nodes(source_device, send_event);

			var marker = g.append("circle")
						.attr("class", "message")
						.attr("r", 7)
						.attr("fill", "white")
						.attr("stroke", "black")
						.attr("stroke-width", 2)
						.attr("opacity", 0.7)
						.attr("transform", "translate(" + src + ")");

			transition(graph, marker, recv_event)
		}


		function transition(graph, marker, recv_event) {
			marker.transition()
			    .duration(event_duration)
			    .attr("transform", "translate(" + dest + ")")
			    .on("end", graph.update_nodes(target_device, recv_event))
			    .remove();
		}


		function get_node_centroid(node) {
        	var bibox = d3.select("." + node).node().getBBox();

	        var t = get_translation(d3.select("." + node).attr("transform")),
    	    	x = t[0] + (bibox.x + bibox.width)/2 - bibox.width / 4,
        		y = t[1] + (bibox.y + bibox.height)/2 - bibox.height / 4;
        	return x + ", " + y;
    	}

    	function get_translation(transform) {
			  var g = document.createElementNS("http://www.w3.org/2000/svg", "g")
			  g.setAttributeNS(null, "transform", transform);
			  var matrix = g.transform.baseVal.consolidate().matrix;
			  
			  return [matrix.e, matrix.f];
			}
	}

	this.set_event_time = function(time) {
		event_duration = time;
	}
}

function Animator(graph, g, _start, _end, _part_id) {
	$.ajax({
	    url: "/events",
	    type: "GET",
	    dataType: 'json',
	    data: { 
	    	start: _start,
			end: _end,
			part_id: _part_id 
		},
	    success: function (d) {
	    	events = d
	    	animate()
	    },
	    error: function () {
	        alert('Error obtaining event data for partition ' + _part_id + ' in range ' + _start + ' to ' + _end + '.');
	    }
	});

	function animate() {
		var i = 0
		for (i = 0; i < events.send.length; i++) {
			create_markers(i)
		}
	}

	function create_markers(i) {
		setTimeout(function() { 
			var msg = new Message(graph, g, events.send[i], events.recv[events.send[i].id]);
			msg.draw();
		}, (events.send[i].time - _start) * 1000)


	}
}

