var dragSrcEl = null;

function handleDragStart(e) {
	dragSrcEl = this;

	e.dataTransfer.effectAllowed = 'move';
	// Store the name of the Game being moved in the transfer object
	e.dataTransfer.setData('text/html', this.getElementsByClassName("name")[0].innerHTML);
}

function handleDrop(e) {
	if (e.stopPropagation) {
		e.stopPropagation();
	}

	if (dragSrcEl != this) {
		//// Figure out the ranks of the rows being dragged or dropped

		// Store the rank of the row on which the drop occurred
		targRow = this.getElementsByClassName("rank")[0].innerHTML;
		
		// Store the rank of the row which is being dragged
		srcRow = dragSrcEl.getElementsByClassName("rank")[0].innerHTML;

		//// Update the local HTML

		// Copy the destination row's game name to the source row
		dragSrcEl.getElementsByClassName("name")[0].innerHTML = 
			this.getElementsByClassName("name")[0].innerHTML;

		// Replace the destination row's game name with the one stored in the xfer data
		this.getElementsByClassName("name")[0].innerHTML = 
			e.dataTransfer.getData('text/html');

		// TODO: Change the drop behavior from swapping to inserting

		//// Tell the server of the change
		var name = document.getElementById("username").innerHTML;

		req = new XMLHttpRequest();
		req.open("GET", "table_test.html?username=" + name + "&src=" + srcRow + "&dest=" + targRow, true);
		req.send();
	}

	return false;
}

function handleDragOver(e) {
  if (e.preventDefault) {
    e.preventDefault();
  }

  return false;
}

function handleDragEnter(e) {
}

function handleDragLeave(e) {
}

function handleDragEnd(e) {

}

// Makes the rows draggable
function votingEnable() {
	// Find every table element and set draggable property to true
	rows = document.getElementsByClassName('rowNoDrag');

	// I have no idea why the code below works, but it was the only way
	// I could get all the rows to be updated
	var i;
	for (i = 0; i < rows.length; i++) {
		rows[i].setAttribute('draggable', 'true');
	}
	var max = rows.length;
	for (i = 0; i < max; i++) {
		// Apparently changing the class adjusts the 'rows' variable
		// automatically???  But not if you combine this for loop with
		// the one above it???
		rows[0].setAttribute('class', 'row'); 
	}
}

// Disables dragging of the rows
function votingDisable() {
	// Find every table element and set draggable property to false
	rows = document.getElementsByClassName('row');

	var i;
	for (i = 0; i < rows.length; i++) {
		rows[i].setAttribute('draggable', 'false');
	}
	var max = rows.length;
	for (i = 0; i < max; i++) {
		rows[0].setAttribute('class', 'rowNoDrag');
	}
}

var rows = document.querySelectorAll('#candidates .rowNoDrag');
[].forEach.call(rows, function(row) {
	// Register DnD event handlers
	row.addEventListener('dragstart', handleDragStart, false);
    row.addEventListener('dragenter', handleDragEnter, false)
    row.addEventListener('dragover', handleDragOver, false);
    row.addEventListener('dragleave', handleDragLeave, false);
	row.addEventListener('drop', handleDrop, false)  
    row.addEventListener('dragend', handleDragEnd, false);;
});
