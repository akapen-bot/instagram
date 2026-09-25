# -*- coding: utf-8 -*-
"""
その日の予定になっている投稿をInstagramへ公開する

GitHub Actions から毎日1回呼ばれる。
schedule.json に今日の日付の投稿があれば公開し、なければ何もしない。

必要な環境変数:
    IG_USER_ID        Instagramのユーザーid
    IG_ACCESS_TOKEN   長期アクセストークン
    GITHUB_REPOSITORY Actionsが自動で入れる（画像URLの組み立てに使う）
    DRY_RUN           1 にすると実際には公開せず、内容だけ表示する
"""
import json, os, sys, time, urllib.parse, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
GRAPH = os.environ.get('GRAPH_BASE', 'https://graph.instagram.com/v23.0')
IG_ID = os.environ.get('IG_USER_ID', '')
TOKEN = os.environ.get('IG_ACCESS_TOKEN', '')
DRY = os.environ.get('DRY_RUN', '') == '1'
JST = datetime.timezone(datetime.timedelta(hours=9))

POSTED_LOG = os.path.join(HERE, 'posted.log')


def api(path, params, method='POST'):
    """Graph APIを呼ぶ。失敗したら中身を見せて止まる"""
    params = dict(params, access_token=TOKEN)
    url = '%s/%s' % (GRAPH, path.lstrip('/'))
    data = urllib.parse.urlencode(params).encode()
    if method == 'GET':
        url += '?' + data.decode()
        data = None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')
        print('APIエラー %s %s\n%s' % (e.code, path, body), file=sys.stderr)
        raise


def wait_ready(container_id, tries=20, wait=5):
    """コンテナの準備が終わるまで待つ。すぐ公開すると失敗することがある"""
    for _ in range(tries):
        r = api(container_id, {'fields': 'status_code,status'}, method='GET')
        code = r.get('status_code')
        if code == 'FINISHED':
            return True
        if code == 'ERROR':
            print('コンテナの作成に失敗しました: %s' % r.get('status'), file=sys.stderr)
            return False
        time.sleep(wait)
    print('コンテナの準備がtimeoutしました', file=sys.stderr)
    return False


def already_posted(no):
    if not os.path.exists(POSTED_LOG):
        return False
    with open(POSTED_LOG, encoding='utf-8') as f:
        return any(line.split('\t')[0] == str(no) for line in f if line.strip())


def record(no, label, media_id):
    with open(POSTED_LOG, 'a', encoding='utf-8') as f:
        f.write('%s\t%s\t%s\t%s\n' % (
            no, datetime.datetime.now(JST).isoformat(timespec='seconds'), label, media_id))


def publish(post, raw_base):
    urls = ['%s/%s' % (raw_base, p) for p in post['images']]
    print('画像 %d枚' % len(urls))
    for u in urls:
        print('  ' + u)

    if DRY:
        print('--- DRY_RUN のため公開しません ---')
        print(post['caption'][:200] + ' …')
        return None

    # 1. 1枚ずつコンテナを作る
    children = []
    for u in urls:
        r = api('%s/media' % IG_ID, {'image_url': u, 'is_carousel_item': 'true'})
        children.append(r['id'])
        print('  コンテナ %s' % r['id'])

    # 2. カルーセルとしてまとめる
    r = api('%s/media' % IG_ID, {
        'media_type': 'CAROUSEL',
        'children': ','.join(children),
        'caption': post['caption'],
    })
    carousel = r['id']
    print('カルーセル %s' % carousel)

    if not wait_ready(carousel):
        sys.exit(1)

    # 3. 公開する
    r = api('%s/media_publish' % IG_ID, {'creation_id': carousel})
    print('公開しました media_id=%s' % r.get('id'))
    return r.get('id')


def main():
    if not IG_ID or not TOKEN:
        # まだトークンを登録していない間は、毎朝エラー通知が来ないよう正常終了する
        print('IG_USER_ID / IG_ACCESS_TOKEN が未設定です。')
        print('Metaでトークンを取得したら、リポジトリの Settings → Secrets に登録してください。')
        print('設定が済むまで、この処理は何もしません。')
        return

    with open(os.path.join(HERE, 'schedule.json'), encoding='utf-8') as f:
        sched = json.load(f)

    repo = os.environ.get('GITHUB_REPOSITORY')
    raw_base = (sched.get('raw_base')
                or (repo and 'https://raw.githubusercontent.com/%s/main/images' % repo))
    if not raw_base:
        print('画像URLの起点が決まりません。GITHUB_REPOSITORY か raw_base を設定してください',
              file=sys.stderr)
        sys.exit(1)

    today = datetime.datetime.now(JST).date().isoformat()
    todays = [p for p in sched['posts'] if p['date'] == today]
    if not todays:
        print('%s は投稿予定がありません' % today)
        return

    for post in todays:
        if already_posted(post['no']):
            print('#%03d はすでに投稿済みです。とばします' % post['no'])
            continue
        print('=== #%03d %s (%s) ===' % (post['no'], post['label'], post['date']))
        media_id = publish(post, raw_base)
        if media_id:
            record(post['no'], post['label'], media_id)


if __name__ == '__main__':
    main()
