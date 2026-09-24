# 赤ペン英作文 自動投稿

`schedule.json` に書かれた日付になると、GitHub Actions がその日の投稿を
Instagram へ公開する。PCの電源は関係ない。

```
post.py                     投稿スクリプト
schedule.json               いつ・どの画像・どのキャプションを出すか
images/010/1.jpg …          投稿する画像
posted.log                  投稿済みの記録（二重投稿を防ぐ）
.github/workflows/post.yml            毎日 JST 8:00 に実行
.github/workflows/refresh-token.yml   毎週 トークンを更新
```

---

## セットアップ

### 1. Metaでアプリを作る

1. [developers.facebook.com](https://developers.facebook.com) にInstagramと同じアカウントでログイン
2. **マイアプリ → アプリを作成**
3. ユースケースは **「Instagramの投稿を管理」** 系を選ぶ
   （名称は変わることがある。Instagram APIが使えるものを選ぶ）
4. アプリ名は任意（例：`akapen-poster`）

### 2. Instagramをつなぐ

1. アプリの管理画面 → **Instagram** を追加
2. **「Instagramログインでビジネス向けInstagram API」** 側を選ぶ
   （Facebookページは不要なほう）
3. **アクセス許可**で次の2つを有効にする
   - `instagram_business_basic`
   - `instagram_business_content_publish`
4. 自分のInstagramアカウントを接続する

> 自分のアカウントにしか投稿しないなら、**アプリ審査は不要**。
> 開発モードのままで動く。

### 3. トークンとIDを取る

1. アプリ管理画面のツールから **アクセストークンを生成**
2. 出てきた短期トークンを **長期トークン（60日）** に変換する
3. あわせて **Instagramユーザーid**（数字の羅列）を控える

取得したトークンは**チャットに貼らないこと**。
メモ帳などでローカルのファイルに保存しておく。

### 4. GitHubのSecretsに登録

リポジトリ → Settings → Secrets and variables → Actions → New repository secret

| 名前 | 中身 |
|---|---|
| `IG_USER_ID` | Instagramユーザーid |
| `IG_ACCESS_TOKEN` | 長期アクセストークン |
| `GH_PAT` | トークン自動更新用（下記） |

`GH_PAT` は、このリポジトリに対して **Secrets: 書き込み** 権限を持つ
fine-grained personal access token。
なくても投稿はできるが、60日ごとに手作業でトークンを入れ直すことになる。

### 5. テストする

Actions → **投稿** → Run workflow → `dry_run` に `1` を入れて実行。

公開せずに、どの画像とキャプションを使うかだけ表示される。
問題なければ `0` で本番実行。

---

## 運用

- 投稿は**毎日 JST 8:00** に自動実行。その日の予定がなければ何もしない
- 投稿するとリポジトリの `posted.log` に記録が残る。同じ回を二重に投稿しない
- 画像や日程を変えたいときは、`インスタ/build_repo.py` を実行して push し直す

## うまくいかないとき

| 症状 | 見るところ |
|---|---|
| APIエラー 190 | トークンが切れている。手順3をやり直す |
| APIエラー 100 / 画像が取得できない | リポジトリが**公開**になっているか確認 |
| バージョンエラー | `post.py` の `GRAPH_BASE` のバージョンを新しいものに上げる |
| 何も起きない | Actions のログを見る。`投稿予定がありません` なら日付が合っていない |
