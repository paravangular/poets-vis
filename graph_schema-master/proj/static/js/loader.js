function load_graph_instance(filename) {
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function(){
  		if(xmlhttp.readyState === 4 && xmlhttp.status === 200) {

			var xmlDoc = xmlhttp.responseXML;

			var graphProperties = xmlDoc.getElementsByTagName("GraphInstance")[0].getElementsByTagName("Properties");
			var p = JSON.parse("{" + graphProperties[0].innerHTML + "}");

			var nodesList = xmlDoc.getElementsByTagName("DevI");
			var nodes = {};

			for (var i = 0; i < nodesList.length; i++) {
				var n = nodesList[i];
				var id = n.getAttribute("id");
		   		var type = n.getAttribute("type");
				var prop = JSON.parse("{" + n.childNodes[1].innerHTML + "}"); // gets the p element

				var node = { "id": id,
				       		"type": type,
				       		"p": prop }

				nodes[id] = node;
			}

			var edgesList = xmlDoc.getElementsByTagName("EdgeI");
			var edges = [];

			for (var i = 0; i < edgesList.length; i++) {
				var n = edgesList[i];
		   		var reSource = /(.+):in/
		   		var reTarget = /-(.+):out/
		   		var path = n.getAttribute("path")
		   		var source = reSource.exec(path)[1];
		   		var target = reTarget.exec(path)[1];
				       		
				var edge = {"source": source,
				       		"target": target}

				edges.push(edge);
			}

		   	var data = {
		   		"nodes": nodes,
		   		"edges": edges,
		   		"p": p
		   	}
		   	return data;
		}
	}
	xmlhttp.open("GET", filename, false);
	xmlhttp.send();

	return xmlhttp.onreadystatechange();
}

function load_node_props(filename) {
	var xmlhttp = new XMLHttpRequest();
	
	xmlhttp.onreadystatechange = function(){
  		if(xmlhttp.readyState === 4 && xmlhttp.status === 200) {
  			var props = [];
			var xmlDoc = xmlhttp.responseXML;
			var devTypes = xmlDoc.getElementsByTagName("DeviceType");

			for (var i = 0; i < devTypes.length; i++) {
				var prop = devTypes[i].getElementsByTagName("State")[0].childNodes;
				
				for (var j = 1; j < prop.length; j += 2) {
					var name = prop[j].getAttribute("name");
					props.push(name);
				}
				
			}

			return props;
			
		}
	}
	xmlhttp.open("GET", filename, false);
	xmlhttp.send();

	return xmlhttp.onreadystatechange();
}

function load_initial_graph_state(filename, graph_instance) {
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function(){
  		if(xmlhttp.readyState === 4 && xmlhttp.status === 200) {

			var xmlDoc = xmlhttp.responseXML;
			var initEvents = xmlDoc.getElementsByTagName("InitEvent");

			for (var i = 0; i < initEvents.length; i++) {
				var n = initEvents[i];
				var id = n.getAttribute("dev");
				var prop = JSON.parse("{" + n.childNodes[1].innerHTML + "}"); // gets the p element

				var node = graph_instance.nodes[id];
				Object.assign(node.p, prop);
			}

		   	return;
		}
	}
	xmlhttp.open("GET", filename, false);
	xmlhttp.send();

	return xmlhttp.onreadystatechange();

}

function load_graph_events(filename) {
	var xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
		if(xmlhttp.readyState === 4 && xmlhttp.status === 200) {
			var events = { "send": [],
							"recv": [] }

			var xmlDoc = xmlhttp.responseXML;
			var sendEvents = xmlDoc.getElementsByTagName("SendEvent");
			var recvEvents = xmlDoc.getElementsByTagName("RecvEvent");

			for (var i = 0; i < sendEvents.length; i++) {
				var eventXml = sendEvents[i];
				var evt = {};

				for (var j = 0; j < eventXml.attributes.length; j++) {
					  var attr = eventXml.attributes[j];
					  evt[attr.name] = attr.value; 
				}

				var s = JSON.parse("{" + eventXml.childNodes[1].innerHTML + "}");
				var m = JSON.parse("{" + eventXml.childNodes[3].innerHTML + "}");

				evt.node_prop = s;
				evt.msg_prop = m;
				evt.type = "send";

				events.send.push(evt);
			}

			for (var i = 0; i < recvEvents.length; i++) {
				var eventXml = recvEvents[i];
				var evt = {};

				for (var j = 0; j < eventXml.attributes.length; j++) {
					  var attr = eventXml.attributes[j];
					  evt[attr.name] = attr.value; 
				}

				var s = JSON.parse("{" + eventXml.childNodes[1].innerHTML + "}");

				evt.node_prop = s;
				evt.type = "recv";
				events.recv.push(evt);
			}

			return events;
		}
	}

	xmlhttp.open("GET", filename, false); // TODO: false is deprecated
	xmlhttp.send();
	return xmlhttp.onreadystatechange();
}

function load_property_menu(props) {
	for (var p = 0; p < props.length; p++) {
		var radio = $('<input type="radio" name="property" value= "' + props[p] + '">' + props[p] + '<br>');
    	radio.appendTo('#property-menu');
	}

}