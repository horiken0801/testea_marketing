/**
 * 新規状況表v2.0 → SATORI 連携：判定ロジック（シートやAPIに触れない純粋な関数だけ）
 *
 * 日付は timezone の影響を避けるため YYYYMMDD の整数（例: 20260831）で扱う。
 * Node からもテストできるよう、GAS 固有の API はこのファイルでは使わない。
 */

var SATORI_STATUS = {
  PENDING: '未決',
  FORMER: '元在',
  ENROLLED: '在籍',
  ACTIVE: '対応中',
};

var SATORI_EMAIL_RE = /[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/g;
var SATORI_FULL_DATE_RE = /(\d{4})[-\/.年](\d{1,2})[-\/.月](\d{1,2})/;
var SATORI_MONTH_DAY_RE = /(^|[^\d\/])(\d{1,2})\/(\d{1,2})(?![\d\/])/g;
var SATORI_TRUTHY = ['true', '1', 'yes', 'y', 'on', 'はい', '済', '○', '〇', '◯', '✓', '✔', '☑', 'レ'];
// 年なし日付（MM/DD）が、行を遡ったときに何日以上「進んで」いたら年をまたいだとみなすか
var SATORI_YEAR_WRAP_DAYS = 120;

function satoriNormalize(value) {
  return String(value == null ? '' : value).normalize('NFKC').trim();
}

function satoriExtractEmails(value) {
  return (satoriNormalize(value).match(SATORI_EMAIL_RE) || []).map(function (e) { return e.toLowerCase(); });
}

function satoriIsChecked(value) {
  return SATORI_TRUTHY.indexOf(satoriNormalize(value).toLowerCase()) >= 0;
}

function satoriYmd(y, m, d) {
  var date = new Date(Date.UTC(y, m - 1, d));
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) return null;
  return y * 10000 + m * 100 + d;
}

function satoriYmdToDate(ymd) {
  return new Date(Date.UTC(Math.floor(ymd / 10000), Math.floor(ymd / 100) % 100 - 1, ymd % 100));
}

function satoriAddDays(ymd, days) {
  var d = satoriYmdToDate(ymd);
  d.setUTCDate(d.getUTCDate() + days);
  return d.getUTCFullYear() * 10000 + (d.getUTCMonth() + 1) * 100 + d.getUTCDate();
}

/** 「2026-08-03 0:00:00」「2026/8/3」などの年付き日付。無ければ null。 */
function satoriParseFullDate(value) {
  var m = satoriNormalize(value).match(SATORI_FULL_DATE_RE);
  return m ? satoriYmd(+m[1], +m[2], +m[3]) : null;
}

/** 年なしの「MM/DD」をすべて [月, 日] で返す（「8/3 8/10」のような複数記載にも対応）。 */
function satoriParseMonthDays(value) {
  var text = satoriNormalize(value);
  if (SATORI_FULL_DATE_RE.test(text)) return [];
  var result = [];
  var m;
  SATORI_MONTH_DAY_RE.lastIndex = 0;
  while ((m = SATORI_MONTH_DAY_RE.exec(text)) !== null) {
    var month = +m[2], day = +m[3];
    if (month >= 1 && month <= 12 && day >= 1 && day <= 31) result.push([month, day]);
  }
  return result;
}

function satoriHasDate(value) {
  return satoriParseFullDate(value) !== null || satoriParseMonthDays(value).length > 0;
}

/**
 * 問合日を行ごとに YYYYMMDD で返す。年なし（MM/DD）の問合日は年を推定する。
 * 旧シートから統合した行は校舎ごとに時系列で並んだ「MM/DD」のまとまりなので、
 * まとまりの最後の行を anchor 以前で最も新しい年とし、遡りながら年をまたいだところで年を1つ減らす。
 */
function satoriInferInquiryDates(rows, campusIdx, inquiryIdx, anchorYmd) {
  var dates = rows.map(function (r) { return satoriParseFullDate(r[inquiryIdx]); });
  var blocks = [], current = null, currentCampus = null;
  rows.forEach(function (row, i) {
    var campus = satoriNormalize(row[campusIdx]);
    if (satoriParseMonthDays(row[inquiryIdx]).length) {
      if (current === null || campus !== currentCampus) {
        current = [];
        blocks.push(current);
      }
      current.push(i);
      currentCampus = campus;
    } else if (dates[i] !== null || campus !== currentCampus) {
      current = null;
      currentCampus = null;
    }
  });

  var anchorMonth = Math.floor(anchorYmd / 100) % 100, anchorDay = anchorYmd % 100, anchorYear = Math.floor(anchorYmd / 10000);
  blocks.forEach(function (block) {
    var later = null, year = null;
    for (var k = block.length - 1; k >= 0; k--) {
      var i = block[k];
      var md = satoriParseMonthDays(rows[i][inquiryIdx])[0];
      if (year === null) {
        year = (md[0] < anchorMonth || (md[0] === anchorMonth && md[1] <= anchorDay)) ? anchorYear : anchorYear - 1;
      } else if ((md[0] - later[0]) * 31 + (md[1] - later[1]) > SATORI_YEAR_WRAP_DAYS) {
        year -= 1;
      }
      later = md;
      dates[i] = satoriYmd(year, md[0], md[1]);
    }
  });
  return dates;
}

/** 対応日付のセルを YYYYMMDD の配列にする。年なしは問合日以降で最も近い日付とみなす。 */
function satoriActivityDates(value, inquiryYmd) {
  var full = satoriParseFullDate(value);
  if (full !== null) return [full];
  if (inquiryYmd === null) return [];
  var floor = satoriAddDays(inquiryYmd, -7), baseYear = Math.floor(inquiryYmd / 10000);
  var result = [];
  satoriParseMonthDays(value).forEach(function (md) {
    for (var y = baseYear; y <= baseYear + 1; y++) {
      var d = satoriYmd(y, md[0], md[1]);
      if (d !== null && d >= floor) { result.push(d); break; }
    }
  });
  return result;
}

/** 基準日の前月末（例: 20260929 → 20260831）。 */
function satoriPrevMonthEnd(todayYmd) {
  var first = Math.floor(todayYmd / 100) * 100 + 1;
  return satoriAddDays(first, -1);
}

/**
 * 1行分の判定。返り値 { status, write, reason }
 *   status: 未決 / 元在 / 在籍 / 対応中 / null
 *   write : SATORIへ書き込む状態か（在籍は最近の入会・再入会だけ書き込む）
 */
function satoriDeriveRow(row, idx, inquiry, cutoff, conf) {
  if (satoriHasDate(row[idx.withdrawn])) return { status: SATORI_STATUS.FORMER, write: true, reason: '退会日あり' };
  var rejoined = satoriIsChecked(row[idx.rejoin]) || satoriHasDate(row[idx.rejoin]);
  if (rejoined) return { status: SATORI_STATUS.ENROLLED, write: true, reason: '再入会' };
  var enrolled = satoriActivityDates(row[idx.enrollment], inquiry);
  var enrolledYmd = enrolled.length ? Math.max.apply(null, enrolled) : null;
  if (satoriHasDate(row[idx.enrollment])) {
    var recent = enrolledYmd !== null && enrolledYmd >= conf.enrolledWriteSince;
    return { status: SATORI_STATUS.ENROLLED, write: recent, reason: recent ? '入会（最近）' : '入会（以前）' };
  }
  if (satoriNormalize(row[idx.status]) === SATORI_STATUS.FORMER) {
    return { status: SATORI_STATUS.FORMER, write: true, reason: '在籍ステータス: 元在' };
  }
  if (inquiry === null) return { status: null, write: false, reason: '' };

  var dates = [inquiry];
  idx.activity.forEach(function (c) { dates = dates.concat(satoriActivityDates(row[c], inquiry)); });
  var last = Math.max.apply(null, dates);
  if (last > cutoff) return { status: SATORI_STATUS.ACTIVE, write: true, reason: '対応中（最終 ' + last + '）' };
  return { status: SATORI_STATUS.PENDING, write: true, reason: cutoff + 'までに対応停止（最終 ' + last + '）' };
}

// 同じメールアドレスに複数行あるときの優先順位（小さいほど優先）
function satoriRank(result) {
  if (result.status === SATORI_STATUS.ENROLLED) return result.reason === '再入会' ? 0 : (result.write ? 1 : 2);
  return { '対応中': 3, '未決': 4, '元在': 5 }[result.status];
}

/**
 * シートの全行から、メールアドレスごとのあるべき状態を作る。
 * 返り値: { email: { status, permissionReject, tag, reason, inquiry } }
 *   status が null のときは SATORI の現在の状態に触れない。
 */
function satoriBuildDesired(rows, idx, todayYmd, conf) {
  var cutoff = satoriPrevMonthEnd(todayYmd);
  var inquiries = satoriInferInquiryDates(rows, idx.campus, idx.inquiry, conf.yearInferenceAnchor);
  var byEmail = {};

  rows.forEach(function (row, rowNo) {
    var emails = satoriExtractEmails(row[idx.email]);
    if (!emails.length) return;
    var doNotSend = satoriIsChecked(row[idx.doNotSend]);
    var spam = satoriIsChecked(row[idx.spam]);
    var result = spam ? { status: null } : satoriDeriveRow(row, idx, inquiries[rowNo], cutoff, conf);

    emails.forEach(function (email) {
      var e = byEmail[email] || (byEmail[email] = { permissionReject: false, best: null, rank: null, rowNo: -1, inquiry: null, route: '' });
      e.permissionReject = e.permissionReject || doNotSend;
      if (idx.route !== undefined && satoriNormalize(row[idx.route])) e.route = satoriNormalize(row[idx.route]);  // 下の行（新しい行）を優先
      if (!result.status) return;
      var rank = satoriRank(result);
      if (e.best === null || rank < e.rank || (rank === e.rank && rowNo > e.rowNo)) {
        e.best = result; e.rank = rank; e.rowNo = rowNo; e.inquiry = inquiries[rowNo];
      }
    });
  });

  var desired = {};
  Object.keys(byEmail).forEach(function (email) {
    var e = byEmail[email];
    var status = e.best && e.best.write ? e.best.status : null;
    var tag = (status === SATORI_STATUS.PENDING || status === SATORI_STATUS.FORMER) &&
      e.inquiry !== null && e.inquiry >= conf.tagInquirySince;
    desired[email] = {
      status: status,
      permissionReject: e.permissionReject,
      tag: tag,
      reason: e.best ? e.best.reason : '',
      inquiry: e.inquiry,
      route: e.route,
    };
  });
  return desired;
}

/**
 * あるべき状態と、前回までに送った状態（ログ）を比べて、送る変更を作る。
 * sent: { email: { status, permission, tag } }
 * 返り値: [{ email, status, permission, appendTag, deleteTag }]（変更がある項目だけ値が入る）
 */
function satoriDiff(desired, sent, conf) {
  var changes = [];
  Object.keys(desired).forEach(function (email) {
    var d = desired[email], s = sent[email] || { status: '', permission: '', tag: false };
    var change = { email: email, status: '', permission: '', appendTag: '', deleteTag: '' };
    if (d.status && d.status !== s.status) change.status = d.status;
    if (d.permissionReject && s.permission !== conf.permissionDenied) change.permission = conf.permissionDenied;
    if (d.tag && !s.tag) change.appendTag = conf.tagName;
    if (!d.tag && s.tag) change.deleteTag = conf.tagName;
    if (change.status || change.permission || change.appendTag || change.deleteTag) changes.push(change);
  });
  return changes;
}

/**
 * バルクAPI用のCSV文字列（空欄の項目は SATORI 側で上書きされない）。
 * routes を渡すと collection_route（情報獲得経路）列も付ける（{ email: { route } }）。
 */
function satoriBuildCsv(changes, conf, routes) {
  var header = ['email', 'custom:' + conf.statusField, 'delivery_permission', 'append_tags', 'delete_tags'];
  if (routes) header.push('collection_route');
  var quote = function (v) { v = String(v); return /[",\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  var lines = [header.join(',')];
  changes.forEach(function (c) {
    var cells = [c.email, c.status, c.permission ? 'reject' : '', c.appendTag, c.deleteTag];
    if (routes) cells.push((routes[c.email] && routes[c.email].route) || conf.routeDefault);
    lines.push(cells.map(quote).join(','));
  });
  return lines.join('\n') + '\n';
}

if (typeof module !== 'undefined') {
  module.exports = {
    SATORI_STATUS: SATORI_STATUS,
    satoriExtractEmails: satoriExtractEmails,
    satoriParseFullDate: satoriParseFullDate,
    satoriParseMonthDays: satoriParseMonthDays,
    satoriInferInquiryDates: satoriInferInquiryDates,
    satoriActivityDates: satoriActivityDates,
    satoriPrevMonthEnd: satoriPrevMonthEnd,
    satoriBuildDesired: satoriBuildDesired,
    satoriDiff: satoriDiff,
    satoriBuildCsv: satoriBuildCsv,
  };
}
