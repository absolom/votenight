var dragSrcEl = null;

function handleDragStart(e) {
	dragSrcEl = this;

	e.dataTransfer.effectAllowed = 'move';
	// Store the name of the Game being moved in the transfer object
	e.dataTransfer.setData('text/html', this.getElementsByClassName("name")[0].innerHTML);
}

function gameButtonLostFocus() {
	var table = document.getElementById("candidates");

    // Remove the form from the add game row
    var addRow = table.lastElementChild;
    var form = addRow.lastElementChild;
    try {  // In case it was already removed!
	    addRow.removeChild(form);
	}
	catch(err) {
	}

    // Reenable clickability of add game row
	document.getElementsByClassName("rowAdd")[0].setAttribute("onclick", "addGameButtonClicked()");
}

function addGameButtonClicked() {
	// Add a form for the game's name
	var inp = document.createElement("input");
	inp.setAttribute("id", "gamename");
	inp.setAttribute("class", "gameNameInput");
	inp.setAttribute("onkeypress", "gameNameKeyPress()");
	inp.setAttribute("type", "text");
	inp.setAttribute("placeholder", "Game Name");
	inp.setAttribute("name", "gamename");
	inp.setAttribute("required", "true");
	inp.setAttribute("onblur", "gameButtonLostFocus()");

	document.getElementsByClassName("rowAdd")[0].appendChild(inp);

	// Bring the input box into focus
	inp.focus();

	// Disable clickability on the add game row
	document.getElementsByClassName("rowAdd")[0].removeAttribute("onclick");
}

function onLoad() {
	// Turn voting on.
	votingEnable();

	// Check if the user has a username stored on their computer.
	var username = localStorage.getItem("username");
	if(username != null) {
		var form = document.forms["loginForm"];
		if(form != null) {
			var field = form["username"];
			if(field != null) {
				// They did have a username stored, so fill in the login form and submit it
				// to autologin.
				field.value = username;
				form.submit();
			}
		}
	}
}

function gameNameKeyPress(e) {
	if (!e) e  = window.event;
	var keyCode = e.keyCode || e.which;
	if (keyCode == 13) {
		//// Submit a request to add the game
		// Get the new game's name from the input
		var gamename = document.getElementById("gamename").value;

		// Validate user entry
		if(gamename == null || gamename == "" || gamename.length < 3) {
			alert("Game name must be longer than 2 characters...");
			return false;
		}

		// Create and send the request
		req = new XMLHttpRequest();
		req.open("GET", "votenight.html?gamename=" + gamename, true);
		req.send();

		//// Also add the game to the local HTML
		var table = document.getElementById("candidates");

		// Create the new entry
		var nw = document.createElement("div");
		nw.setAttribute("class", "row");
		nw.setAttribute("draggable", "true");

			var rank = table.children.length - 3;
			rank = rank + 1;

			var chld = document.createElement("span");
			chld.setAttribute("class", "rank");
			chld.innerHTML = rank.toString();
			nw.appendChild(chld);

			chld = document.createElement("span");
			chld.setAttribute("class", "name");
			chld.innerHTML = gamename;
			nw.appendChild(chld);

		// Add the new row
		table.insertBefore(nw, table.lastElementChild);

		// Register drag and drop handlers on new row
		nw.addEventListener('dragstart', handleDragStart, false);
	    nw.addEventListener('dragenter', handleDragEnter, false)
	    nw.addEventListener('dragover', handleDragOver, false);
	    nw.addEventListener('dragleave', handleDragLeave, false);
		nw.addEventListener('drop', handleDrop, false);
	    nw.addEventListener('dragend', handleDragEnd, false);

	    // Remove form and make add game row clickable
	    gameButtonLostFocus();

		return false;
	}
}

// function validateGameName() {
// }

function validateUsername() {
	var x = document.forms["loginForm"]["username"].value;
	if (x == null || x == "" || x.length < 3) {
		alert("Username must be longer than 2 characters...");
		return false;
	}
	for (var i = 0; i < x.length; i++)
	{
		if(x[i] == ' ')
		{
			alert("Username must not have spaces...");
			return false;
		}
	}
	localStorage.setItem("username", x);
}

function handleDrop(e) {
	if (e.stopPropagation) {
		e.stopPropagation();
	}

	if (dragSrcEl != this) {
		//// Figure out the ranks of the rows being dragged or dropped

		// Store the rank of the row on which the drop occurred
		targRow = parseInt(this.getElementsByClassName("rank")[0].innerHTML);

		// Store the rank of the row which is being dragged
		srcRow = parseInt(dragSrcEl.getElementsByClassName("rank")[0].innerHTML);

		//// Update the local HTML

		table = document.getElementById('candidates');

		if(srcRow > targRow) {  // Target is above the source on the screen
			// Move all those at or below target down one
			for(var i = srcRow; i > targRow; i--) {
				document.getElementsByClassName("name")[i-1].innerHTML =
					document.getElementsByClassName("name")[i-2].innerHTML;
			}
			document.getElementsByClassName("name")[targRow-1].innerHTML =
				e.dataTransfer.getData('text/html');
		}
		else {  // Target is below the source on the screen
			for(var i = srcRow; i < targRow; i++) {
				document.getElementsByClassName("name")[i-1].innerHTML =
					document.getElementsByClassName("name")[i].innerHTML;
			}
			document.getElementsByClassName("name")[targRow-1].innerHTML =
				e.dataTransfer.getData('text/html');
		}

		//// Tell the server of the change
		var name = document.getElementById("username").innerHTML;

		req = new XMLHttpRequest();
		req.open("GET", "votenight.html?username=" + name + "&src=" + srcRow + "&dest=" + targRow, true);
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
	row.addEventListener('drop', handleDrop, false);
    row.addEventListener('dragend', handleDragEnd, false);
});
