// SatoriLogic.gs の判定ロジックのテスト: node satori_sync/gas/test_logic.js
const assert = require('assert');
const path = require('path');
const L = require(path.join(__dirname, 'SatoriLogic.gs'));

const CONF = {
  tagName: '新規_未決元在',
  tagInquirySince: 20260601,
  enrolledWriteSince: 20260901,
  yearInferenceAnchor: 20260929,
  permissionDenied: '拒否',
  statusField: 'custom_situation',
};
const HEADER = ['校舎', '問合日', '初期対応へのレス', '面談実施', '体験実施', '入会', '再入会', 'メールアドレス', '退会日',
  '在籍ステータス', '営業・取材・スパムフラグ', '送付禁止フラグ'];
const IDX = {
  campus: 0, inquiry: 1, enrollment: 5, rejoin: 6, email: 7, withdrawn: 8, status: 9, spam: 10, doNotSend: 11,
  activity: [1, 2, 3, 4],
};
const ROWS = [
  ['久我山校', '2026-07-10 0:00:00', '2026/07/11', '2026/08/05', '', '', 'FALSE', 'Taro@Example.com', '', '体験実施済', 'FALSE', 'TRUE'],
  ['久我山校', '2017-04-28 0:00:00', '', '', '', '', '', 'old@example.com', '', '未決', 'FALSE', 'FALSE'],
  ['久我山校', '2018-01-01', '', '', '', '', '', 'ｈａｎａｋｏ＠ｅｘａｍｐｌｅ．ｃｏｍ', '', '元在', 'FALSE', 'FALSE'],
  ['駒込校', '2025-01-01', '', '', '', '', 'TRUE', 'hanako@example.com', '', '入会', 'FALSE', 'FALSE'],
  ['日吉校', '2024-01-01', '', '', '', '2024/02/01', '', 'a@example.com / b@example.com', '2025/03/31', '退会', 'FALSE', 'TRUE'],
  ['日吉校', '2026-08-20', '', '', '', '', '', 'sales@example.com', '', '未対応', 'TRUE', 'FALSE'],
  ['日吉校', '2026-08-25', '', '2026/08/28', '2026/09/03', '', '', 'sept@example.com', '', '体験実施済', 'FALSE', 'FALSE'],
  ['日吉校', '2026-09-02', '', '', '', '', '', 'new@example.com', '', '未対応', 'FALSE', 'FALSE'],
  ['初台校', '2026-02-23', '', '', '', '', '', 'again@example.com', '', '未対応', 'FALSE', 'FALSE'],
  ['初台校', '2026-09-05', '', '', '', '', '', 'again@example.com', '', '未対応', 'FALSE', 'FALSE'],
  ['自由が丘校', '2026-07-01', '', '2026/07/10', '', '2026/09/10', '', 'joined@example.com', '', '入会', 'FALSE', 'FALSE'],
  ['自由が丘校', '2023-01-01', '', '', '', '2023/02/01', '', 'oldjoin@example.com', '', '入会', 'FALSE', 'FALSE'],
  ['田町校', '11/20', '', '11/25', '', '', '', 'md1@example.com', '', '面談実施済', 'FALSE', 'FALSE'],
  ['田町校', '06/10', '', '', '', '', '', 'md3@example.com', '', '未対応', 'FALSE', 'FALSE'],
];

const tests = {
  'メールアドレス抽出（全角・複数・大文字）'() {
    assert.deepStrictEqual(L.satoriExtractEmails('Ａ@Ｅｘａｍｐｌｅ.com / b@x.jp'), ['a@example.com', 'b@x.jp']);
  },
  '日付の解析'() {
    assert.strictEqual(L.satoriParseFullDate('2026-08-05 0:00:00'), 20260805);
    assert.strictEqual(L.satoriParseFullDate('02/01'), null);
    assert.deepStrictEqual(L.satoriParseMonthDays('8/3 8/10'), [[8, 3], [8, 10]]);
    assert.deepStrictEqual(L.satoriParseMonthDays('リスケ'), []);
  },
  '前月末（年またぎ）'() {
    assert.strictEqual(L.satoriPrevMonthEnd(20270115), 20261231);
    assert.strictEqual(L.satoriPrevMonthEnd(20260301), 20260228);
  },
  '年なし問合日の年推定'() {
    const rows = ['03/01', '12/20', '01/05', '05/10'].map((d) => ['A', d]).concat([['B', '10/01']]);
    assert.deepStrictEqual(L.satoriInferInquiryDates(rows, 0, 1, 20260929), [20250301, 20251220, 20260105, 20260510, 20251001]);
  },
  '年なし対応日は問合日以降'() {
    assert.deepStrictEqual(L.satoriActivityDates('01/10', 20251215), [20260110]);
  },
  '9/29時点の判定'() {
    const d = L.satoriBuildDesired(ROWS, IDX, 20260929, CONF);
    const st = (e) => d[e].status;
    assert.strictEqual(st('taro@example.com'), '未決');
    assert.strictEqual(d['taro@example.com'].tag, true);
    assert.strictEqual(d['taro@example.com'].permissionReject, true);
    assert.strictEqual(st('old@example.com'), '未決');
    assert.strictEqual(d['old@example.com'].tag, false);
    assert.strictEqual(st('hanako@example.com'), '在籍');   // 再入会
    assert.strictEqual(st('b@example.com'), '元在');        // 退会日
    assert.strictEqual(st('sales@example.com'), null);      // 営業
    assert.strictEqual(st('sept@example.com'), '対応中');   // 9月に対応あり
    assert.strictEqual(st('new@example.com'), '対応中');    // 9月の問合せ
    assert.strictEqual(st('again@example.com'), '対応中');  // 2月は停止・9月に再問合せ
    assert.strictEqual(st('joined@example.com'), '在籍');   // 9月の入会は書き込む
    assert.strictEqual(st('oldjoin@example.com'), null);    // 以前の入会は触れない
    assert.strictEqual(st('md1@example.com'), '未決');
    assert.strictEqual(st('md3@example.com'), '未決');
    assert.strictEqual(d['md3@example.com'].tag, true);
  },
  '翌月になると9月で止まった人が未決になる'() {
    const d = L.satoriBuildDesired(ROWS, IDX, 20261005, CONF);
    assert.strictEqual(d['sept@example.com'].status, '未決');
    assert.strictEqual(d['sept@example.com'].tag, true);
    assert.strictEqual(d['new@example.com'].status, '未決');
  },
  '差分: 未決→対応中でタグを外す・変化なしは送らない'() {
    const desired = {
      'x@example.com': { status: '対応中', permissionReject: false, tag: false },
      'y@example.com': { status: '未決', permissionReject: true, tag: true },
      'z@example.com': { status: '未決', permissionReject: false, tag: true },
    };
    const sent = {
      'x@example.com': { status: '未決', permission: '', tag: true },
      'z@example.com': { status: '未決', permission: '', tag: true },
    };
    assert.deepStrictEqual(L.satoriDiff(desired, sent, CONF), [
      { email: 'x@example.com', status: '対応中', permission: '', appendTag: '', deleteTag: '新規_未決元在' },
      { email: 'y@example.com', status: '未決', permission: '拒否', appendTag: '新規_未決元在', deleteTag: '' },
    ]);
  },
  'CSV'() {
    const csv = L.satoriBuildCsv([{ email: 'x@example.com', status: '対応中', permission: '', appendTag: '', deleteTag: '新規_未決元在' }], CONF);
    assert.strictEqual(csv, 'email,custom:custom_situation,delivery_permission,append_tags,delete_tags\nx@example.com,対応中,,,新規_未決元在\n');
    const withRoute = L.satoriBuildCsv([{ email: 'x@example.com', status: '対応中', permission: '', appendTag: '', deleteTag: '' }],
      Object.assign({ routeDefault: 'SATORI通常問い合わせフォーム' }, CONF), {});
    assert.ok(withRoute.endsWith('x@example.com,対応中,,,,SATORI通常問い合わせフォーム\n'));
  },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  try {
    fn();
    console.log('ok   ' + name);
  } catch (e) {
    failed++;
    console.log('FAIL ' + name + '\n' + e.message);
  }
}
if (failed) process.exit(1);
