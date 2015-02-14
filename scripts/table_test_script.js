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
		//// Update the local HTML

		// Copy the destination row's game name to the source row
		dragSrcEl.getElementsByClassName("name")[0].innerHTML = 
			this.getElementsByClassName("name")[0].innerHTML;

		// Replace the destination row's game name with the one stored in the xfer data
		this.getElementsByClassName("name")[0].innerHTML = 
			e.dataTransfer.getData('text/html');

		// TODO: Change the drop behavior from swapping to inserting

		//// Tell the server of the change
		// TODO: Implement
		// req = new XMLHttpRequest();
		// req.open("POST", "", false);
		// req.send();
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

var rows = document.querySelectorAll('#candidates .row');
[].forEach.call(rows, function(row) {
	row.addEventListener('dragstart', handleDragStart, false);
    row.addEventListener('dragenter', handleDragEnter, false)
    row.addEventListener('dragover', handleDragOver, false);
    row.addEventListener('dragleave', handleDragLeave, false);
	row.addEventListener('drop', handleDrop, false)  
    row.addEventListener('dragend', handleDragEnd, false);;
});
