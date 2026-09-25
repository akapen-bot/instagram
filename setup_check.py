# -*- coding: utf-8 -*-
"""
取得したトークンを確認する

token.txt にトークンを貼って保存してから実行すると、
・そのトークンが有効か
・Instagramのユーザーidはいくつか
・あと何日で切れるか
・投稿権限があるか
を表示する。トークンそのものは画面に出さない。

使い方:
    1. token.txt にトークンだけを貼って保存（.gitignore済み）
    2. python setup_check.py
"""
import json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GRAPH = os.environ.get('GRAPH_BASE', 'https://graph.instagram.com/v23.0')


def get(path, token, **params):
    params['access_token'] = token
    url = '%s/%s?%s' % (GRAPH, path.lstrip('/'), urllib.parse.urlencode(params))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {'_error': e.read().decode('utf-8', 'replace'), '_code': e.code}


def main():
    path = os.path.join(HERE, 'token.txt')
    if not os.path.exists(path):
        print('token.txt がありません。トークンだけを貼ったファイルを作ってください。')
        sys.exit(1)
    token = open(path, encoding='utf-8').read().strip()
    if not token:
        print('token.txt が空です。')
        sys.exit(1)

    print('トークンの長さ: %d文字（中身は表示しません）' % len(token))

    me = get('me', token, fields='id,username,account_type')
    if '_error' in me:
        print('\n認証に失敗しました。トークンを取り直してください。')
        print(me['_error'][:400])
        sys.exit(1)

    print('\n=== 接続できました ===')
    print('ユーザー名      : @%s' % me.get('username'))
    print('Instagramユーザーid: %s' % me.get('id'))
    print('アカウント種別  : %s' % me.get('account_type', '（取得できず）'))

    # 有効期限を調べる（更新はせず、残り日数だけ見る）
    r = get('refresh_access_token', token, grant_type='ig_refresh_token')
    if 'expires_in' in r:
        print('残り有効期間    : 約%d日' % (r['expires_in'] // 86400))
        print('※ いま更新されたので、この新しいトークンを使ってください:')
        print('   token.txt を上書きします')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(r['access_token'])
    else:
        print('残り有効期間    : 取得できず（短期トークンの可能性があります）')
        if '_error' in r:
            print('  ' + r['_error'][:200])

    print('\n次にやること:')
    print('  このまま「準備できた」と伝えてください。')
    print('  IG_USER_ID と IG_ACCESS_TOKEN をGitHubへ登録します。')


if __name__ == '__main__':
    main()
