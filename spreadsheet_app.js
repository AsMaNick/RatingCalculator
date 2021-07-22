var ss = SpreadsheetApp.getActiveSpreadsheet();

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
  return 50 * points / max_points * (2 * participants - 2) / (participants + place - 2);
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
  for (var i = 0; i < data.results.length; ++i) {
    if (data.online_judge == "codeforces") {
      sheet.getRange(2 + i, 1).setValue(data.results[i].place);
    } else {
      sheet.getRange(2 + i, 1).setValue(data.results[i].place);
      sheet.getRange(2 + i, 1).setFormula(getAtCoderResultLink(data.contest_id, data.results[i]));
    }
    sheet.getRange(2 + i, 2).setValue(data.results[i].user.name);
    sheet.getRange(2 + i, 3).setFormula(getProfileLink(data.online_judge, data.results[i].user));
    sheet.getRange(2 + i, 4).setValue(data.results[i].points);
    sheet.getRange(2 + i, 5).setValue(data.results[i].penalty);
    sheet.getRange(2 + i, 6).setValue(data.results[i].is_rated);
    var ratingITMO = getRatingITMO(data.results[0].points, data.results.length, data.results[i].points, data.results[i].place);
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

function getRowByHandle(onlineJudge) {
  var sheet = ss.getSheetByName("OJ Rating");
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

function addStandingsToTheMainRating(data) {
  var sheet = ss.getSheetByName("OJ Rating");
  var rowByHandle = getRowByHandle(data.online_judge);
  var column = sheet.getLastColumn() + 1;
  sheet.getRange(2, column).setValue(data.start_date);
  sheet.getRange(3, column).setFormula(getStandingsLink(data.online_judge, data.contest_id, data.sheet_name));
  for (var i = 0; i < data.results.length; ++i) {
    var handle = getHandle(data.online_judge, data.results[i].user);
    if (handle in rowByHandle) {
      sheet.getRange(rowByHandle[handle], column).setFormula(`=getRatingCoefficient(INDIRECT("R3C${column}"; FALSE)) * '${data.sheet_name}'!G${i + 2}`);
    }
  }
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
  if (onlineJudge == "codeforces") {
      return SpreadsheetApp.newTextStyle()
        .setForegroundColor(getCodeforcesRatingColor(rating))
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
  var sheet = ss.getSheetByName("OJ Rating");
  var rowByHandle = getRowByHandle(data.online_judge);
  myLog(rowByHandle);
  for (var i = 0; i < data.ratings.length; ++i) {
    var handle = data.ratings[i].handle;
    if (handle in rowByHandle) {
      if (data.online_judge == "codeforces") {
        sheet.getRange(rowByHandle[handle], 3).setTextStyle(getHandleTextStyle(data.online_judge, data.ratings[i].new_rating));
        sheet.getRange(rowByHandle[handle], 5).setValue(`${data.ratings[i].old_rating} → ${data.ratings[i].new_rating}`);
        const [r, g, b] = getRatingDiffColor(data.ratings[i].new_rating - data.ratings[i].old_rating);
        sheet.getRange(rowByHandle[handle], 5).setBackgroundRGB(r, g, b);
      }
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
