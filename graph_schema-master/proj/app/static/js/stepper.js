function Stepper(_part_id, _max_level) {
	snapshots = null;

	$.ajax({
	    url: "/stepper",
	    type: "GET",
	    dataType: 'json',
	    data: { 
			part_id: _part_id,
			max_level: _max_level
		},
	    success: function (d) {
	    	snapshots = d;
	    },
	    error: function () {
	        alert('Error obtaining snapshot data for partition ' + _part_id);
	    }
	});

	this.get_snapshots = function() {
		return snapshots;
	}
}