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

function getRatingITMO(max_points, participants, points, place) {
  if (max_points == 0) {
    return 0;
  }
  if (participants == 1) {
    return 100;
  }
  return 50 * points / max_points * (2 * participants - 2) / (participants + place - 2);
}

function doPost(e) {
  var lock = LockService.getPublicLock(); 
  lock.waitLock(30000);
  try {
    var data = JSON.parse(e.postData.contents);
    myLog(data);
    myLog(data.sheet_name);
    myLog(data.results);
    if (!sheetExists(data.sheet_name)) {
      var sheet = ss.insertSheet();
      sheet.setName(data.sheet_name);
      sheet.setColumnWidth(1, 75);
      sheet.setColumnWidth(2, 300);
      sheet.setColumnWidth(3, 150);
      sheet.setColumnWidth(4, 75);
      sheet.setColumnWidth(5, 75);
      sheet.setColumnWidth(6, 75);
      sheet.getRange(1, 1).setValue("Место");
      sheet.getRange(1, 2).setValue("Участник");
      sheet.getRange(1, 3).setValue("Handle");
      sheet.getRange(1, 4).setValue("Балл");
      sheet.getRange(1, 5).setValue("Штраф");
      sheet.getRange(1, 6).setValue("Рейтинг");
      for (var i = 0; i < data.results.length; ++i) {
        sheet.getRange(2 + i, 1).setValue(data.results[i].place);
        sheet.getRange(2 + i, 2).setValue(data.results[i].user.name);
        sheet.getRange(2 + i, 3).setFormula(getProfileLink(data.online_judge, data.results[i].user));
        sheet.getRange(2 + i, 4).setValue(data.results[i].points);
        sheet.getRange(2 + i, 5).setValue(data.results[i].penalty);
        var ratingITMO = getRatingITMO(data.results[0].points, data.results.length, data.results[i].points, data.results[i].place);
        sheet.getRange(2 + i, 6).setValue(+ratingITMO.toFixed(2));
      }
    }
  } finally {
    lock.releaseLock();
  }
}
