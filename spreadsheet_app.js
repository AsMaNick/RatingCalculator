var ss = SpreadsheetApp.getActiveSpreadsheet();
var table_name = 'OJ Rating 2021 autumn';
var codeforcesListKey = 'cd0882df077418b2f43db6b6756e25df';

function myLog(msg) {
  var logSht = ss.getSheetByName('DebugLog'); 
  const nxtLogRow = logSht.getLastRow() + 1;
  logSht.getRange('A'+ nxtLogRow).setValue(msg);
}

function sheetExists(sheetName) {
  if (ss.getSheetByName(sheetName)) {
    return true;
  }
  return false;
}

function getProfileLink(onlineJudge, user) {
  if (onlineJudge == "codeforces") {
    return `=HYPERLINK("https://codeforces.com/profile/${user.codeforces_handle}"; "${user.codeforces_handle}")`;
  } else if (onlineJudge == "atcoder") {
    return `=HYPERLINK("https://atcoder.jp/users/${user.atcoder_handle}"; "${user.atcoder_handle}")`;
  } else {
    return `${onlineJudge}/${handle}`;
  }
}

function getAtCoderResultLink(contestId, result) {
  return `=HYPERLINK("https://atcoder.jp/contests/${contestId}/standings?watching=${result.user.atcoder_handle}"; ${result.place})`
}

function getStandingsLink(onlineJudge, constestId, text) {
  if (onlineJudge == "codeforces") {
    if (codeforcesListKey != '') {
      return `=HYPERLINK("https://codeforces.com/contest/${constestId}/standings?list=${codeforcesListKey}"; "${text}")`;
    }
    return `=HYPERLINK("https://codeforces.com/contest/${constestId}/standings"; "${text}")`;
  } else if (onlineJudge == "atcoder") {
    return `=HYPERLINK("https://atcoder.jp/contests/${constestId}/standings"; "${text}")`;
  } else {
    return `${text}`;
  }
}

function getRatingITMO(max_points, participants, points, place) {
  if (max_points == 0) {
    return 0;
  }
  if (participants == 1) {
    return 100;
  }
  return Math.min(100, 50 * points / max_points * (2 * participants - 2) / (participants + place - 2));
}

function createStandings(data) {
  var sheet = ss.insertSheet(data.sheet_name, ss.getNumSheets());
  sheet.setColumnWidth(1, 75);
  sheet.setColumnWidth(2, 300);
  sheet.setColumnWidth(3, 150);
  sheet.setColumnWidth(4, 75);
  sheet.setColumnWidth(5, 75);
  sheet.setColumnWidth(6, 75);
  sheet.setColumnWidth(7, 75);
  sheet.getRange(1, 1).setFormula(getStandingsLink(data.online_judge, data.contest_id, "Место"));
  sheet.getRange(1, 2).setValue("Участник");
  sheet.getRange(1, 3).setValue("Handle");
  sheet.getRange(1, 4).setValue("Балл");
  sheet.getRange(1, 5).setValue("Штраф");
  sheet.getRange(1, 6).setValue("Is Rated");
  sheet.getRange(1, 7).setValue("Рейтинг");
  var winnerPoints = 0;
  for (var result of data.results) {
    if (result.user.is_official) {
      winnerPoints = result.points;
      break;
    }
  }
  for (var i = 0; i < data.results.length; ++i) {
    var ratingITMO = getRatingITMO(winnerPoints, data.official_participants, data.results[i].points, data.results[i].place);
    if (!data.results[i].user.is_official) {
      data.results[i].place = "-";
    }
    if (data.online_judge == "codeforces") {
      sheet.getRange(2 + i, 1).setValue(data.results[i].place);
      sheet.getRange(2 + i, 1).setHorizontalAlignment("right");
    } else {
      sheet.getRange(2 + i, 1).setValue(data.results[i].place);
      sheet.getRange(2 + i, 1).setFormula(getAtCoderResultLink(data.contest_id, data.results[i]));
    }
    sheet.getRange(2 + i, 2).setValue(data.results[i].user.name);
    sheet.getRange(2 + i, 3).setFormula(getProfileLink(data.online_judge, data.results[i].user));
    sheet.getRange(2 + i, 4).setValue(data.results[i].points);
    sheet.getRange(2 + i, 5).setValue(data.results[i].penalty);
    sheet.getRange(2 + i, 6).setValue(data.results[i].is_rated);
    sheet.getRange(2 + i, 7).setValue(+ratingITMO.toFixed(2));
  }
}

function getHandle(onlineJudge, user) {
  if (onlineJudge == "codeforces") {
    return user.codeforces_handle;
  } else if (onlineJudge == "atcoder") {
    return user.atcoder_handle;
  }
  return "-";
}

function getRatingCoefficientFormula(cell) {
  return `=IF(ISERROR(SEARCH("AGC"; ${cell})); IF(ISERROR(SEARCH("ARC"; ${cell})); IF(ISERROR(SEARCH("ABC"; ${cell})); IF(ISERROR(SEARCH("Div. 1 + Div. 2"; ${cell})); IF(ISERROR(SEARCH("Div. 1"; ${cell})); IF(ISERROR(SEARCH("Div. 2"; ${cell})); IF(ISERROR(SEARCH("Div. 3"; ${cell})); 0; 'Config'!B8); 'Config'!B7); 'Config'!B6); 'Config'!B5); 'Config'!B4); 'Config'!B3); 'Config'!B2)`;
}

function getRowByHandle(onlineJudge) {
  var sheet = ss.getSheetByName(table_name);
  var participants;
  if (onlineJudge == "codeforces") {
    participants = sheet.getRange(`C4:C${sheet.getLastRow()}`).getValues();
  } else {
    participants = sheet.getRange(`D4:D${sheet.getLastRow()}`).getValues();
  }
  rowByHandle = {};
  for (var i = 0; i < participants.length; ++i) {
    rowByHandle[participants[i][0]] = i + 4;
  }
  return rowByHandle;
}

function sortByTotalRating() {
  var sheet = ss.getSheetByName(table_name);
  const lastRow = sheet.getLastRow();
  const lastColumn = sheet.getLastColumn();
  var range = sheet.getRange(4, 1, lastRow - 3, lastColumn);
  range.sort({column: 7, ascending: false});
  var places = sheet.getRange(`A4:A${sheet.getLastRow()}`).getValues();
  var currentPlace = 0;
  for (var i = 0; i < places.length; ++i) {
    var place = places[i][0];
    if (place != '-') {
      ++currentPlace;
      place = currentPlace;
    }
    places[i][0] = place;
  }
  sheet.getRange(`A4:A${sheet.getLastRow()}`).setValues(places);
}

function addStandingsToTheMainRating(data) {
  var sheet = ss.getSheetByName(table_name);
  var rowByHandle = getRowByHandle(data.online_judge);
  var column = sheet.getLastColumn() + 1;
  sheet.getRange(1, column).setFormula(getRatingCoefficientFormula(`INDIRECT("R3C${column}"; FALSE)`));
  sheet.getRange(2, column).setValue(data.start_date);
  sheet.getRange(3, column).setFormula(getStandingsLink(data.online_judge, data.contest_id, data.sheet_name));
  for (var i = 0; i < data.results.length; ++i) {
    var handle = getHandle(data.online_judge, data.results[i].user);
    if (handle in rowByHandle) {
      sheet.getRange(rowByHandle[handle], column).setFormula(`=IF('${data.sheet_name}'!F${i + 2}; 1; Config!F2) * INDIRECT("R1C${column}"; FALSE) * '${data.sheet_name}'!G${i + 2}`);
    }
  }
  sortByTotalRating();
}

function getCodeforcesRatingColor(rating) {
  if (rating <= 0) {
    return "#000000";
  } else if (rating < 1200) {
    return "#808080";
  } else if (rating < 1400) {
    return "#008000";
  } else if (rating < 1600) {
    return "#03a89e";
  } else if (rating < 1900) {
    return "#0000ff";
  } else if (rating < 2100) {
    return "#a000a0";
  } else if (rating < 2400) {
    return "#ff8c00";
  }
  return "#ff0000";
}

function getAtcoderRatingColor(rating) {
  if (rating <= 0) {
    return "#000000";
  } else if (rating < 400) {
    return "#808080";
  } else if (rating < 800) {
    return "#804000";
  } else if (rating < 1200) {
    return "#008000";
  } else if (rating < 1600) {
    return "#00c0c0";
  } else if (rating < 2000) {
    return "#0000ff";
  } else if (rating < 2400) {
    return "#c0c000";
  } else if (rating < 2800) {
    return "#ff8000";
  }
  return "#ff0000";
}

function getRatingColor(onlineJudge, rating) {
  if (onlineJudge == "codeforces") {
    return getCodeforcesRatingColor(rating);
  } else if (onlineJudge == "atcoder") {
    return getAtcoderRatingColor(rating);
  }
  return "#000000";
}

function getRatingDiffColor(delta) {
  if (delta == 0) {
    return [255, 255, 255];
  }
  var r = 0, g = 0, b = 0, alpha = (15 + 2 * Math.abs(delta)) / 800;
  if (delta < 0) {
    r = 255;
  } else {
    g = 255;
  }
  var nr = Math.max(0, Math.min(255, parseInt((1 - alpha) * 255 + alpha * r + 0.5)));
  var ng = Math.max(0, Math.min(255, parseInt((1 - alpha) * 255 + alpha * g + 0.5)));
  var nb = Math.max(0, Math.min(255, parseInt((1 - alpha) * 255 + alpha * b + 0.5)));
  return [nr, ng, nb];
}

function getHandleTextStyle(onlineJudge, rating) {
  if (onlineJudge == "codeforces" || onlineJudge == "atcoder") {
      return SpreadsheetApp.newTextStyle()
        .setForegroundColor(getRatingColor(onlineJudge, rating))
        .setUnderline(false)
        .setBold(rating > 0)
        .build();
  }
  return SpreadsheetApp.newTextStyle().build();
}

function actionCreateStandings(data) {
  if (!sheetExists(data.sheet_name)) {
    createStandings(data);
    addStandingsToTheMainRating(data);
  }
}

function actionUpdateRatings(data) {
  myLog("action update");
  var sheet = ss.getSheetByName(table_name);
  var rowByHandle = getRowByHandle(data.online_judge);
  var handlesColumn = 3;
  if (data.online_judge == "atcoder") {
    ++handlesColumn;
  }
  for (var i = 0; i < data.ratings.length; ++i) {
    var handle = data.ratings[i].handle;
    if (handle in rowByHandle) {
      sheet.getRange(rowByHandle[handle], handlesColumn).setTextStyle(getHandleTextStyle(data.online_judge, data.ratings[i].new_rating));
      sheet.getRange(rowByHandle[handle], handlesColumn + 2).setValue(`${data.ratings[i].old_rating} → ${data.ratings[i].new_rating}`);
      const [r, g, b] = getRatingDiffColor(data.ratings[i].new_rating - data.ratings[i].old_rating);
      sheet.getRange(rowByHandle[handle], handlesColumn + 2).setBackgroundRGB(r, g, b);
    } else {
      myLog(`FAIL, cann't find user ${handle}`);
    }
  }
}

function doPost(e) {
  var lock = LockService.getPublicLock(); 
  lock.waitLock(30000);
  try {
    var data = JSON.parse(e.postData.contents);
    myLog(data);
    if (data.action == "add_standings") {
      actionCreateStandings(data);
    } else if (data.action == "update_ratings") {
      actionUpdateRatings(data);
    }
  } finally {
    lock.releaseLock();
  }
}
