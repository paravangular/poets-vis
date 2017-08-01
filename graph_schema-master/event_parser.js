// First parse the initial state of nodes (GraphSnapshot,  orchestratorTime="0")
// then parse send events from 

xmlhttp = new XMLHttpRequest();
xmlhttp.onload = function() {
	var lines = xmlhttp.responseText.split('\n');

	for (int i = 0; i < lines.length; i++) {
		if (lines[i].startsWith("Send:")) {
			var source_id = /\s(.+):out/.exec(lines[i]);
			var curr_spin = /curr_spin\s=\s(-?\d)/.exec(lines[i]);

			i++
			var send_again = /sendAgain\s=\s(\d)/.exec(lines[i]);

			var prop = {
				"curr_spin" : curr_spin,
				"send_again": send_again
			};

			package_event(source_id, "out", prop); // from "out" port
		}
	}

}

xmlhttp.open("GET","ising_spin_16_2_event.txt", true);
xmlhttp.send();

function package_event(source_id, port, properties) {
	var evt = {
		"port" : port,
		"id": source_id,
		"prop": properties // properties of source node that have changed due to this event
	}

}