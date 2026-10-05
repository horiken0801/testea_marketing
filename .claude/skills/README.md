# .claude/skills/

[coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills)(MIT License, `LICENSE` 参照)から取り込んだClaude Codeマーケティングスキル集です。

Claude Codeがこのリポジトリで作業する際、ここに含まれる各スキルの `SKILL.md` を読み込み、関連するタスク(CRO・コピーライティング・SEO・広告・メール・SNSなど)で自動的に適用します。

## 更新方法

```bash
git clone --depth 1 https://github.com/coreyhaines31/marketingskills.git /tmp/marketingskills
rm -rf .claude/skills/*
cp -r /tmp/marketingskills/skills/* .claude/skills/
cp /tmp/marketingskills/LICENSE .claude/skills/LICENSE
```

更新後は `VERSIONS.md`(本家リポジトリ)で変更点を確認してください。

このディレクトリ配下のファイルは独自に編集せず、カスタマイズが必要な場合は本家の `CONTRIBUTING.md` に従うか、別ディレクトリに独自スキルとして追加してください。
