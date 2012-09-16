/* General Functions */

function resize(img, resizeWidth) {
	if (img.width > img.height) {
		img.className += " friend-img-wide";
		var offsetPercent = (img.width*resizeWidth/img.height - resizeWidth)/2;
		img.style.left = "-" + offsetPercent + "px";
	} else {
		img.className += " friend-img-high";
	}
	img.style.display = "block";
}

function padToTwoDigits (n) { return (n < 10) ? '0'+n : n }

function ISODateString(date) {
	var dateParts = date.split(' ');
	var date = dateParts[0];
	var time = dateParts[1];
	var hoursBehindUTC = Math.round(new Date().getTimezoneOffset()/60);

	var isoDate = date + 'T' + time + ':00-' + padToTwoDigits(hoursBehindUTC) + '00';

	return isoDate;
}
function postToUrl(url, functionName, data) {
	$.ajax({
	  type: 'POST',
	  url: url,
	  data: data,
	  success: eval(functionName + 'Succeeded'),
	  error: eval(functionName + 'Failed'),
	  dataType: 'JSON',
	});
}
function getFromUrl(url, functionName) {
	$.ajax({
	  type: 'GET',
	  url: url,
	  data: {},
	  success: eval(functionName + 'Succeeded'),
	  error: eval(functionName + 'Failed'),
	  dataType: 'JSON',
	});
}

/* Create Event */

function createEventSucceeded(data) {
	var event_id = data.event_id;
	var event_name = $('#inputName').get(0).value;
	//console.log(event_name);
	window.location.href = window.location.origin + "/invite_friends/" + event_id + "/" + event_name;
}

function createEventFailed(data) {
	console.log(data);
}

function createEvent() {
	var eventData = {}
	
	eventData['name'] = $('#inputName').get(0).value;
	eventData['description'] = $('#inputDescription').get(0).value;
	eventData['location'] = $('#inputLocation').get(0).value;
	eventData['start_time'] = ISODateString($('#inputStarts').get(0).value);
	eventData['end_time'] = ISODateString($('#inputEnds').get(0).value);
	
	if (eventData['start_time'] != eventData['end_time']) {
		postToUrl("/_push_event_to_facebook", "createEvent", eventData);
	} else {
		alert("You can't have an event start and end at the same time!");
	}
}

/* Invite friends */

function getAllFbids() {
	var fbids = new Array();
	$('.outer-circle').each(function() {
		if ($(this).hasClass('selected')) {
			fbids.push($(this).attr('fbid'));
		}
	});
	var fbidString = fbids.join(',');
	return fbidString;
}

function getAllFriendIdsAndNames() {
	var friends = new Array();
	$('.outer-circle').each(function() {
		if ($(this).hasClass('selected')) {
			friends.push({"id": $(this).attr('fbid'), "name": $(this).attr('fbname')});
		}
	});
	return friends;
}

/*function inviteFriendsSucceeded(data) {
	//console.log(data);
	var form = $('#createPartyPageForm').get(0);
	if (form) {
		form.submit();
	}
	//window.location.href = window.location.origin + "/party";
}

function inviteFriendsFailed(data) {
	console.log(data);
}*/

function inviteFriends() {
	//var allFbids = getAllFbids();
	var friends = getAllFriendIdsAndNames();

	$('#friendsInput').get(0).value = JSON.stringify(friends);

	var form = $('#createPartyPageForm').get(0);
	if (form) {
		form.submit();
	}

	//var data = {'friends': friends, 'event_id': eventId, 'event_name': eventName };
	//postToUrl("/_invite_friends_to_facebook_event", "inviteFriends", data);
}

