
var totalSongCount; // total number of songs at time of input
var validSongCount; // total number of songs with valid tag data
 
function processSongList(songList) {
    totalSongCount = songList.length;
    validSongCount = songList.length;
    for (i = 0; i < songList.length; i++) {
        processSong(songList[i]);
    }
}
 
var processedSongCount = 0; // number of songs processed so far
var processedSongs = []; // songs with a list of tag names
var tagCount = {}; // cumulative count across all songs for a given tag name
 
function processSong(song) {
    if (song.artist == undefined) {
        song.artist = "";
    }
    if (song.track == undefined) {
        song.track = "";
        console.log(song);
    }
    var url = "http://ws.audioscrobbler.com/2.0/?method=track.gettoptags&artist=" + song.artist.replace(" ", "+") + "&track=" + song.track.replace(" ", "+") + "&autocorrect=1&api_key=74072129a2c412a98b3e092e47640e7a&format=json"; // last.fm getTopTags query
    jQuery.getJSON(url, function (jsonData) {
        try {
            var tagData = jsonData.toptags.tag; // array of tags, each of which contains a name, count, and url
            var tagNames = []; // list of tag names associated with the song
            for (i = 0; i < Math.min(5, tagData.length); i++) { // store the top 5 tag names
                var tag = tagData[i];
                tagNames.push(tag.name);
                if (!(tag.name in tagCount)) {
                    tagCount[tag.name] = 0;
                }
                tagCount[tag.name] += parseInt(tag.count); // add this song's count for the given tag to the cumulative count
            }
            processedSongs.push({
                artist: song.artist,
                track: song.track,
                id: song.id,
                tags: tagNames
            });
        } catch (err) {
            // console.log(err, jsonData)
            validSongCount--; // discard songs without valid tag data
        }
        processedSongCount++;
        if (processedSongCount == totalSongCount) { // once the last song has been processed
            var songGroups = categorizeSongs();
            createPlaylists(songGroups);
        }
    });
}
 
function categorizeSongs() {
    var tagCountArray = []; // convert the tagCount map into an array with [tagName, cumulativeCount] entries
    for (tagName in tagCount) {
        tagCountArray.push([tagName, tagCount[tagName]]);
    }
    tagCountArray.sort(function (a, b) {
        return b[1] - a[1];
    }); // sort the array so that tags with the highest cumulative count are in front
 
    var numSongsCategorized = 0;
    var songCategorized = []; // boolean array indicating whether or not the song at the given index in processedSongs has been categorized
    for (i = 0; i < validSongCount; i++) {
        songCategorized[i] = false;
    }
    var songsInCategory = {}; // map from a category (tag name) to a list of songs in that category
 
    for (i = 0; i < tagCountArray.length; i++) { // for each tag name, from highest count to lowest
        for (j = 0; j < validSongCount; j++) { // for each song with valid tag data
            var tagName = tagCountArray[i][0];
            if (!songCategorized[j] && (processedSongs[j].tags.indexOf(tagName) >= 0)) { // if the song has not already been assigned a category and has the given tag name
                if (!(tagName in songsInCategory)) {
                    songsInCategory[tagName] = [];
                }
                songsInCategory[tagName].push({
                    artist: processedSongs[j].artist,
                    track: processedSongs[j].track,
                    id: processedSongs[j].id
                }); // add the song to the list of songs associated with the current tag name
                songCategorized[j] = true; // the song has been categorized
                numSongsCategorized++;
            }
        }
        if (numSongsCategorized == validSongCount) { // if all songs have been categorized, break
            break;
        }
    }
 
    var songGroups = []; // convert the songsInCategory map to an array with [category, songsInCategory] entries
    for (category in songsInCategory) {
        songGroups.push([category, songsInCategory[category]]);
    }
    songGroups.sort(function (a, b) {
        return b[1].length - a[1].length;
    }); // sort the array so that groups with the most songs are in front
 
    return songGroups;
}
 
var numSuggestedSongs = 0;
var numSuggestedSongsAdded = 0;
var songGroupsWithSuggestions = [];
 
function createPlaylists(songGroups) {
    for (i = 0; i < songGroups.length; i++) {
        var numSongs = songGroups[i][1].length;
        numSuggestedSongs += 1 * numSongs;
    }
 
    for (i = 0; i < songGroups.length; i++) { // for each group of songs
        songGroupsWithSuggestions[i] = [songGroups[i][0], songGroups[i][1].slice(0)]; // copy the given group into songGroupsWithSuggestions
        for (j = 0; j < songGroups[i][1].length; j++) { // for each song in the group
            addSuggestedSong(i, songGroups[i][1][j]);
        }
    }
}
 
function addSuggestedSong(songGroupIndex, song) {
    var url = "http://ws.audioscrobbler.com/2.0/?method=track.getsimilar&artist=" + song.artist.replace(" ", "+") + "&track=" + song.track.replace(" ", "+") + "&autocorrect=1&limit=3&api_key=74072129a2c412a98b3e092e47640e7a&format=json"; // last.fm getSimilar query
    jQuery.getJSON(url, function (jsonData) {
        var i;
        try {
            for (i = 0; i < 1; i++) {
                var suggestedSongArtist = jsonData.similartracks.track[i].artist.name;
                var suggestedSongTrack = jsonData.similartracks.track[i].name;
                console.log("Song similar to", song.track, "by", song.artist, ":", suggestedSongTrack, "by", suggestedSongArtist);
                songGroupsWithSuggestions[songGroupIndex][1].push({
                    artist: suggestedSongArtist,
                    track: suggestedSongTrack
                });
                numSuggestedSongsAdded++;
            }
        } catch (err) {
            // console.log(err, jsonData);
            numSuggestedSongs -= 1 - i;
        }
        console.log(numSuggestedSongsAdded, numSuggestedSongs);
        if (numSuggestedSongsAdded == numSuggestedSongs) { // once the last suggested song has been added
            getSpotifyIDs(); // get the Spotify IDs for the newly added songs
        }
    });
}
 
var numMissingSpotifyIDs = 0;
 
function getSpotifyIDs() {
    for (i = 0; i < songGroupsWithSuggestions.length; i++) {
        for (j = 0; j < songGroupsWithSuggestions[i][1].length; j++) {
            var song = songGroupsWithSuggestions[i][1][j];
            if (song.id == undefined) {
                numMissingSpotifyIDs++;
            }
        }
    }
 
    for (i = 0; i < songGroupsWithSuggestions.length; i++) {
        for (j = 0; j < songGroupsWithSuggestions[i][1].length; j++) {
            var song = songGroupsWithSuggestions[i][1][j];
            if (song.id == undefined) {
                getSpotifyID(i, j, song);
            }
        }
    }
}
 
function getSpotifyID(songGroupIndex, songIndex, song) {
    var url = "http://ws.spotify.com/search/1/track.json?q=" + song.track.replace(" ", "+");
    jQuery.getJSON(url, function (jsonData) {
        try {
            console.log("Spotify information for:", song.track, "by", song.artist, ":", jsonData);
            var i, foundID = false;
            trackLoop: for (i = 0; i < jsonData.tracks.length; i++) {
                for (j = 0; j < jsonData.tracks[i].artists.length; j++) {
                    if (songEquals(song.artist, jsonData.tracks[i].artists[j].name, song.track, jsonData.tracks[i].name)) {
                        console.log("found song at position " + i + ", author " + j + " with id " + jsonData.tracks[i].href.substring(14));
                        foundID = true;
                        break trackLoop;
                    }
                }
            }
            if (foundID) {
                songGroupsWithSuggestions[songGroupIndex][1][songIndex].id = jsonData.tracks[i].href.substring(14);
            } else {
                console.log("id not found", songGroupIndex, songIndex);
            }
        } catch (err) {
            console.log(err, jsonData);
        }
        numMissingSpotifyIDs--;
        if (numMissingSpotifyIDs == 0) {
            var idGroups = [],
                songGroupsWithIDs = [];
            for (i = 0; i < songGroupsWithSuggestions.length; i++) {
                idGroups[i] = [songGroupsWithSuggestions[i][0],
                    []
                ];
                songGroupsWithIDs[i] = [songGroupsWithSuggestions[i][0],
                    []
                ];
                for (j = 0; j < songGroupsWithSuggestions[i][1].length; j++) {
                    var tempSong = songGroupsWithSuggestions[i][1][j];
                    if (tempSong.id != undefined) {
                        idGroups[i][1].push(tempSong.id);
                        songGroupsWithIDs[i][1].push(tempSong);
                    } else {
                        console.log("no id:", tempSong);
                    }
                }
            }
 
            songGroupsWithSuggestions.sort(function (a, b) {
                return b[1].length - a[1].length;
            });
            songGroupsWithIDs.sort(function (a, b) {
                return b[1].length - a[1].length;
            });
            idGroups.sort(function (a, b) {
                return b[1].length - a[1].length;
            });
 
            console.log("all songs + suggestions:", songGroupsWithSuggestions);
            console.log("all songs + suggestions with IDs:", songGroupsWithIDs);
            console.log("all songs, just IDs", idGroups);
        }
    });
}
 
function songEquals(artist1, artist2, track1, track2) {
    var a1 = artist1.toLowerCase();
    var a2 = artist2.toLowerCase();
    var t1 = track1.toLowerCase();
    var t2 = track2.toLowerCase();
    return (a1.indexOf(a2) != -1 || a2.indexOf(a1) != -1) && (t1.indexOf(t2) != -1 || t2.indexOf(t1) != -1);
}

