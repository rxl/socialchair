$(document).ready(function(){

	$(".pitch-wrap-1").show("drop", {}, 800, function(){
		$(".pitch-wrap-2").delay(1000).show("drop", {}, 800, function(){
			$(".pitch-wrap-3").delay(1000).show("drop", {}, 800, function(){
				$(".login-button").show();
			});
		});
	});
	
	
});