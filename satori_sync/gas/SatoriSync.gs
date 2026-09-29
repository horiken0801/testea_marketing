/**
 * 新規状況表v2.0 → SATORI 自動連携（Google Apps Script）
 *
 * - 30分ごとに新規状況表を読み、メールアドレスごとの「あるべき状態」を判定して、
 *   前回送った内容から変わった人だけを SATORI カスタマーバルクAPI（upsert）で送る。
 * - 送った内容は「SATORI連携ログ」シートに記録する（既存の列・既存のGASには触れない）。
 *
 * 判定（締め日 = 実行日の前月末）
 *   退会日あり → 元在 / 再入会にチェック → 在籍 / 最近の入会 → 在籍
 *   締め日より後に問合せ・対応あり → 対応中（未決を解除）
 *   締め日までに対応が止まっている → 未決 / 在籍ステータスが元在 → 元在
 *   送付禁止フラグ → 配信許可を拒否
 *   タグ「新規_未決元在」: 6/1以降の問合せで未決・元在 → 付ける、それ以外になったら外す
 *
 * APIキーは既存のGASと同じスクリプトプロパティを使う（コードに書かない）:
 *   SATORI_API_KEY / SATORI_SECRET_KEY / COMPANY_KEY / COMPANY_SECRET
 * 情報獲得経路（collection_route）が必須と分かった場合は、スクリプトプロパティ SATORI_SEND_ROUTE を "true" にすると、
 * 既存の handleBackgroundSync と同じく「なにで知ったか」（空なら SATORI通常問い合わせフォーム）を送る。
 * 安全のため、スクリプトプロパティ SATORI_DRY_RUN が "false" になるまでは送信せず、
 * 「SATORI連携プレビュー」シートに送る予定の内容を書き出すだけにする。
 */

var SATORI_CONF = {
  sheetName: '新規状況表v2.0_マスター',
  logSheetName: 'SATORI連携ログ',
  previewSheetName: 'SATORI連携プレビュー',
  registrySheetName: 'SATORI登録済み',
  columns: {
    campus: '校舎',
    inquiry: '問合日',
    email: 'メールアドレス',
    status: '在籍ステータス',
    enrollment: '入会',
    rejoin: '再入会',
    withdrawn: '退会日',
    spam: '営業・取材・スパムフラグ',
    doNotSend: '送付禁止フラグ',
    activity: ['問合日', '初期対応へのレス', '面談実施', '体験実施'],
    route: 'なにで知ったか',
  },
  routeDefault: 'SATORI通常問い合わせフォーム',
  statusField: 'custom_situation',
  permissionDenied: '拒否',
  tagName: '新規_未決元在',
  tagInquirySince: 20260601,
  // この日以降の入会は「在籍」を書き込む（それより前の入会は現役か分からないため触れない）
  enrolledWriteSince: 20260901,
  yearInferenceAnchor: 20260929,
  apiBase: 'https://api.satr.jp/api/v4/public/bulk_customers',
  maxRowsPerRequest: 10000,
  timeZone: 'Asia/Tokyo',
};

var SATORI_LOG_HEADER = ['email', '送信済み_現在の状態', '送信済み_配信許可', '送信済み_タグ', '最終送信日時',
  '処理中コード', '処理中_行番号', '処理中_現在の状態', '処理中_配信許可', '処理中_タグ', '失敗回数', '最後のエラー', '判定理由'];
var SATORI_MAX_RETRY = 3;

// ------------------------------------------------------------ 公開関数（エディタ・トリガーから実行）

/** 初回に1回実行：ログ・プレビューシートを作り、30分ごとのトリガーを登録する。 */
function satoriSetup() {
  satoriLogSheet_();
  ScriptApp.getProjectTriggers()
    .filter(function (t) { return t.getHandlerFunction() === 'satoriSync'; })
    .forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('satoriSync').timeBased().everyMinutes(30).create();
}

/**
 * 初回に1回実行：9/29 に手作業で取り込んだ内容を「送信済み」としてログに記録する（APIは呼ばない）。
 * これで、既に反映済みの人に同じ内容を送り直さず、以後の変化だけを送れる。
 */
function satoriInitLog() {
  var desired = satoriBuildDesired_(20260929);
  var sheet = satoriLogSheet_();
  if (sheet.getLastRow() > 1) throw new Error('SATORI連携ログに既にデータがあります。初期化する場合は2行目以降を消してから実行してください。');
  var now = satoriNow_();
  var rows = Object.keys(desired).map(function (email) {
    var d = desired[email];
    // 9/29 の取り込みでは 対応中 は存在せず、在籍は再入会だけ送った
    var sentStatus = d.status === SATORI_STATUS.ACTIVE ? '' : (d.status === SATORI_STATUS.ENROLLED && d.reason !== '再入会' ? '' : (d.status || ''));
    return [email, sentStatus, d.permissionReject ? SATORI_CONF.permissionDenied : '', d.tag ? 'TRUE' : '', now,
      '', '', '', '', '', 0, '', d.reason];
  });
  if (rows.length) sheet.getRange(2, 1, rows.length, SATORI_LOG_HEADER.length).setValues(rows);
}

/** トリガーから30分ごとに実行される本体。 */
function satoriSync() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    var log = satoriReadLog_();
    satoriProcessPending_(log);
    satoriFlushLog_(log);

    var desired = satoriBuildDesired_(satoriTodayYmd_());
    var sent = {};
    Object.keys(log.byEmail).forEach(function (email) {
      var r = log.byEmail[email].values;
      sent[email] = { status: r[1], permission: r[2], tag: r[3] === 'TRUE' || r[3] === true };
    });
    var registry = satoriRegistry_();
    var changes = satoriDiff(desired, sent, SATORI_CONF).filter(function (c) {
      var entry = log.byEmail[c.email];
      if (entry && entry.values[5]) return false;                            // 処理中
      if (entry && Number(entry.values[10]) >= SATORI_MAX_RETRY) return false; // 失敗が続いている
      return !registry || registry[c.email];                                // SATORI未登録の人は新規作成しない
    });

    if (satoriIsDryRun_()) {
      satoriWritePreview_(changes, desired);
      return;
    }
    if (!changes.length) return;
    var credentials = satoriCredentials_();
    for (var start = 0; start < changes.length; start += SATORI_CONF.maxRowsPerRequest) {
      var chunk = changes.slice(start, start + SATORI_CONF.maxRowsPerRequest);
      var code = satoriUpsert_(credentials, satoriBuildCsv(chunk, SATORI_CONF, satoriSendRoute_() ? desired : null));
      satoriMarkPending_(log, chunk, code, desired);
      satoriFlushLog_(log);
    }
  } finally {
    lock.releaseLock();
  }
}

/**
 * APIの動作確認用：スクリプトプロパティ SATORI_TEST_EMAIL のカスタマー1件に「対応中」を送り、結果をログに出す。
 * 情報獲得経路（collection_route）なしで更新できるか、既存の値が変わらないかを確認するために使う。
 */
function satoriTestOne() {
  var email = PropertiesService.getScriptProperties().getProperty('SATORI_TEST_EMAIL');
  if (!email) throw new Error('スクリプトプロパティ SATORI_TEST_EMAIL にテスト用カスタマーのメールアドレスを設定してください。');
  var credentials = satoriCredentials_();
  var csv = satoriBuildCsv([{ email: email, status: SATORI_STATUS.ACTIVE, permission: '', appendTag: '', deleteTag: '' }], SATORI_CONF,
    satoriSendRoute_() ? (function () { var d = {}; d[email] = { route: SATORI_CONF.routeDefault }; return d; })() : null);
  var code = satoriUpsert_(credentials, csv);
  Logger.log('process_code: ' + code);
  for (var i = 0; i < 12; i++) {
    Utilities.sleep(5000);
    var result = satoriStatus_(credentials, code);
    Logger.log(JSON.stringify(result));
    if (result.process_status === 'finished') return;
  }
}

// ------------------------------------------------------------ 判定

function satoriBuildDesired_(todayYmd) {
  var sheet = SpreadsheetApp.getActive().getSheetByName(SATORI_CONF.sheetName);
  var values = sheet.getDataRange().getDisplayValues();
  var header = values[0].map(satoriNormalize);
  var col = function (name) {
    var i = header.indexOf(name);
    if (i < 0) throw new Error('列「' + name + '」が見つかりません');
    return i;
  };
  var c = SATORI_CONF.columns;
  var idx = {
    campus: col(c.campus), inquiry: col(c.inquiry), email: col(c.email), status: col(c.status),
    enrollment: col(c.enrollment), rejoin: col(c.rejoin), withdrawn: col(c.withdrawn),
    spam: col(c.spam), doNotSend: col(c.doNotSend), activity: c.activity.map(col), route: col(c.route),
  };
  var rows = values.slice(1).filter(function (r) { return r.some(function (v) { return String(v).trim(); }); });
  return satoriBuildDesired(rows, idx, todayYmd, SATORI_CONF);
}

// ------------------------------------------------------------ ログ

function satoriLogSheet_() {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName(SATORI_CONF.logSheetName);
  if (!sheet) {
    sheet = ss.insertSheet(SATORI_CONF.logSheetName);
    sheet.getRange(1, 1, 1, SATORI_LOG_HEADER.length).setValues([SATORI_LOG_HEADER]);
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function satoriReadLog_() {
  var sheet = satoriLogSheet_();
  var last = sheet.getLastRow();
  var rows = last > 1 ? sheet.getRange(2, 1, last - 1, SATORI_LOG_HEADER.length).getValues() : [];
  var byEmail = {};
  rows.forEach(function (v, i) { byEmail[String(v[0]).toLowerCase()] = { index: i, values: v }; });
  return { sheet: sheet, rows: rows, byEmail: byEmail };
}

/** ログ1行をメモリ上で更新する（シートへの書き込みは satoriFlushLog_ でまとめて行う）。 */
function satoriWriteLogRow_(log, email, values) {
  var entry = log.byEmail[email];
  if (!entry) {
    entry = log.byEmail[email] = { index: log.rows.length, values: values };
    log.rows.push(values);
  }
  entry.values = values;
  log.rows[entry.index] = values;
}

function satoriFlushLog_(log) {
  if (log.rows.length) log.sheet.getRange(2, 1, log.rows.length, SATORI_LOG_HEADER.length).setValues(log.rows);
}

function satoriEmptyLogRow_(email) {
  return [email, '', '', '', '', '', '', '', '', '', 0, '', ''];
}

function satoriMarkPending_(log, chunk, code, desired) {
  chunk.forEach(function (c, i) {
    var v = (log.byEmail[c.email] || { values: satoriEmptyLogRow_(c.email) }).values.slice();
    v[5] = code;
    v[6] = i + 1;
    v[7] = c.status;
    v[8] = c.permission;
    v[9] = c.appendTag ? 'TRUE' : (c.deleteTag ? 'FALSE' : '');
    v[12] = desired[c.email] ? desired[c.email].reason : '';
    satoriWriteLogRow_(log, c.email, v);
  });
}

/** 処理中の送信の結果を確認し、成功した人を「送信済み」に反映する。 */
function satoriProcessPending_(log) {
  var byCode = {};
  Object.keys(log.byEmail).forEach(function (email) {
    var code = log.byEmail[email].values[5];
    if (code) (byCode[code] = byCode[code] || []).push(email);
  });
  var codes = Object.keys(byCode);
  if (!codes.length) return;
  var credentials = satoriCredentials_();
  var now = satoriNow_();

  codes.forEach(function (code) {
    var result = satoriStatus_(credentials, code);
    if (result.process_status !== 'finished') return;
    // 失敗行の row_number がヘッダーを数えるか分からないため、前後どちらの解釈でも失敗扱いにする
    // （成功していた人は次回送り直すだけなので害はない）
    var failed = {};
    (result.failed_rows || []).forEach(function (f) {
      failed[f.row_number] = f.message;
      failed[f.row_number - 1] = failed[f.row_number - 1] || f.message;
    });
    byCode[code].forEach(function (email) {
      var v = log.byEmail[email].values.slice();
      var index = Number(v[6]);
      if (failed[index]) {
        v[10] = Number(v[10] || 0) + 1;
        v[11] = String(failed[index]).slice(0, 500);
      } else {
        if (v[7]) v[1] = v[7];
        if (v[8]) v[2] = v[8];
        if (v[9] === 'TRUE') v[3] = 'TRUE';
        if (v[9] === 'FALSE') v[3] = '';
        v[4] = now;
        v[10] = 0;
        v[11] = '';
      }
      v[5] = v[6] = v[7] = v[8] = v[9] = '';
      satoriWriteLogRow_(log, email, v);
    });
  });
}

function satoriWritePreview_(changes, desired) {
  var ss = SpreadsheetApp.getActive();
  var sheet = ss.getSheetByName(SATORI_CONF.previewSheetName) || ss.insertSheet(SATORI_CONF.previewSheetName);
  sheet.clearContents();
  var rows = [['email', '現在の状態', '配信許可', 'タグ追加', 'タグ削除', '判定理由', '作成日時（DRY RUN・未送信）']];
  var now = satoriNow_();
  changes.forEach(function (c) {
    rows.push([c.email, c.status, c.permission, c.appendTag, c.deleteTag, desired[c.email] ? desired[c.email].reason : '', now]);
  });
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
}

/** 「SATORI登録済み」シートのA列（メールアドレス）。シートが無ければ null（全員を対象にする）。 */
function satoriRegistry_() {
  var sheet = SpreadsheetApp.getActive().getSheetByName(SATORI_CONF.registrySheetName);
  if (!sheet || sheet.getLastRow() < 1) return null;
  var registry = {};
  sheet.getRange(1, 1, sheet.getLastRow(), 1).getDisplayValues().forEach(function (r) {
    satoriExtractEmails(r[0]).forEach(function (e) { registry[e] = true; });
  });
  return registry;
}

// ------------------------------------------------------------ SATORI API

/** 既存のGAS（handleBackgroundSync）と同じスクリプトプロパティを使う。 */
function satoriCredentials_() {
  var props = PropertiesService.getScriptProperties();
  var names = { user_key: 'SATORI_API_KEY', user_secret: 'SATORI_SECRET_KEY', company_key: 'COMPANY_KEY', company_secret: 'COMPANY_SECRET' };
  var creds = {};
  Object.keys(names).forEach(function (k) {
    var v = props.getProperty(names[k]);
    if (!v) throw new Error('スクリプトプロパティ ' + names[k] + ' が未設定です');
    creds[k] = v;
  });
  return creds;
}

function satoriUpsert_(credentials, csv) {
  var payload = {};
  Object.keys(credentials).forEach(function (k) { payload[k] = credentials[k]; });
  payload.identity_type = 'email';
  payload.customer_csv_file = Utilities.newBlob(csv, 'text/csv', 'customers.csv');
  var res = UrlFetchApp.fetch(SATORI_CONF.apiBase + '/upsert.json', { method: 'post', payload: payload, muteHttpExceptions: true });
  var code = satoriPayload_(JSON.parse(res.getContentText())).process_code;
  if (res.getResponseCode() !== 200 || !code) throw new Error('SATORI upsert 失敗: HTTP ' + res.getResponseCode() + ' ' + res.getContentText());
  return code;
}

function satoriStatus_(credentials, code) {
  var query = Object.keys(credentials).map(function (k) { return k + '=' + encodeURIComponent(credentials[k]); }).join('&');
  var res = UrlFetchApp.fetch(SATORI_CONF.apiBase + '/status.json?' + query + '&process_code=' + encodeURIComponent(code), { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) throw new Error('SATORI status 失敗: HTTP ' + res.getResponseCode() + ' ' + res.getContentText());
  return satoriPayload_(JSON.parse(res.getContentText()));
}

/** 応答の中身を取り出す。実際の応答は {"status":202,"message":"Accepted","body":{...}} の形（ドキュメントの例は message に入る形）。 */
function satoriPayload_(response) {
  if (response.body && typeof response.body === 'object') return response.body;
  if (response.message && typeof response.message === 'object') return response.message;
  return response;
}

// ------------------------------------------------------------ ユーティリティ

function satoriSendRoute_() {
  return PropertiesService.getScriptProperties().getProperty('SATORI_SEND_ROUTE') === 'true';
}

function satoriIsDryRun_() {
  return PropertiesService.getScriptProperties().getProperty('SATORI_DRY_RUN') !== 'false';
}

function satoriTodayYmd_() {
  return Number(Utilities.formatDate(new Date(), SATORI_CONF.timeZone, 'yyyyMMdd'));
}

function satoriNow_() {
  return Utilities.formatDate(new Date(), SATORI_CONF.timeZone, 'yyyy/MM/dd HH:mm');
}
