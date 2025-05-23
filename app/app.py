import json
import logging
import os
from datetime import datetime, timedelta, timezone

import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def convert_to_jst(utc_time_str):
    """
    UTC時間の文字列をJST（日本時間）に変換する関数
    
    Args:
        utc_time_str (str): "2025-04-16T06:18:40.944703Z"のような形式のUTC時間文字列
        
    Returns:
        str: "2025年04月16日 15:18:40"のような形式のJST時間文字列
    """
    try:
        # マイクロ秒部分を含む場合と含まない場合の両方に対応
        if '.' in utc_time_str:
            if utc_time_str.endswith('Z'):
                utc_time_str = utc_time_str[:-1]  # 末尾の'Z'を削除
            dt = datetime.fromisoformat(utc_time_str)
        else:
            # マイクロ秒がない場合
            if utc_time_str.endswith('Z'):
                utc_time_str = utc_time_str[:-1]  # 末尾の'Z'を削除
            dt = datetime.fromisoformat(utc_time_str)
        
        # UTCとして扱う
        dt = dt.replace(tzinfo=timezone.utc)
        
        # JSTに変換（UTC+9）
        jst = dt.astimezone(timezone(timedelta(hours=9)))
        
        # 日本語形式でフォーマット
        return jst.strftime("%Y年%m月%d日 %H:%M:%S")
    except Exception as e:
        logger.error(f"日時変換エラー: {e}, 入力: {utc_time_str}")
        return utc_time_str  # 変換に失敗した場合は元の文字列を返す


def fetch_plugin_info(plugin_name):
    """
    指定されたプラグイン名からDify Marketplaceのプラグイン情報を取得する関数
    
    プラグイン名からAPIエンドポイントを構築し、HTTPリクエストを送信して
    プラグインの詳細情報（バージョン、更新日時など）を取得します。
    
    Args:
        plugin_name (str): プラグイン名またはURL
                          例: "langgenius/openai" または "https://marketplace.dify.ai/plugins/langgenius/openai"
    
    Returns:
        dict or None: 成功した場合はプラグイン情報を含むJSON応答データ、失敗した場合はNone
    
    Raises:
        Exception: HTTPリクエスト中にエラーが発生した場合
    """
    try:
        # プラグイン名からプラグインのパスを抽出
        # 例: https://marketplace.dify.ai/plugins/langgenius/openai → langgenius/openai
        plugin_path = plugin_name.split('/plugins/')[1] if '/plugins/' in plugin_name else plugin_name
        
        # APIエンドポイントを構築
        api_url = f"https://marketplace.dify.ai/api/v1/plugins/{plugin_path}"
        logger.info(f"APIエンドポイントからJSONデータを取得中: {api_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # requestsでGETリクエスト実行
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            try:
                # JSONデータを解析
                data = response.json()
                formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                
                # latest_versionとversion_updated_atを抽出
                plugin_data = data.get("data", {}).get("plugin", {})
                
                # プラグイン情報から直接latest_versionとversion_updated_atを取得
                version_updated_at = plugin_data.get("version_updated_at", plugin_data.get("updated_at", "不明"))
                latest_version = plugin_data.get("latest_version", "不明")
                
                # ログに出力
                logger.info("=== JSONデータを取得しました ===")
                logger.debug(formatted_json)
                
                # latest_versionとversion_updated_atを出力
                logger.info(f"latest_version: {latest_version}")
                logger.info(f"version_updated_at: {version_updated_at}")
                
                return data
            except json.JSONDecodeError:
                logger.error("JSONデータの解析に失敗しました")
                return None
        else:
            logger.error(f"APIリクエスト中にエラーが発生しました: ステータスコード {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        return None

def load_plugins_from_env():
    """
    環境変数からプラグインリストを読み込む関数
    
    環境変数「PLUGINS」からカンマ区切りのプラグインリスト（plugin1,plugin2,plugin3 の形式）を
    読み込み、リストとして返します。
    
    Returns:
        list: プラグイン名のリスト
    
    Raises:
        ValueError: PLUGINS環境変数が設定されていない場合
    """
    # PLUGINS環境変数を取得
    plugins = os.environ.get('PLUGINS')
    if not plugins:
        raise ValueError("PLUGINSが環境変数に設定されていません。")
    
    # カンマ区切りのプラグインリストを分割
    plugin_names = [plugin.strip() for plugin in plugins.split(',')]
    logger.info(f"環境変数から{len(plugin_names)}個のプラグインを読み込みました")
    return plugin_names

def extract_plugin_version_info(plugin_data, plugin_name):
    """
    プラグインデータから重要なバージョン情報を抽出する関数
    
    APIから取得したプラグインデータから、名前、ID、最新バージョン、更新日時などの
    重要な情報を抽出し、整形された辞書として返します。日時情報はJST（日本時間）に変換されます。
    
    Args:
        plugin_data (dict): APIから取得したプラグイン情報を含む辞書
        plugin_name (str): プラグイン名（URL生成に使用）
    
    Returns:
        dict or None: 抽出されたプラグイン情報を含む辞書、データが無効な場合はNone
    """
    if not plugin_data or "data" not in plugin_data or "plugin" not in plugin_data["data"]:
        return None
    
    plugin = plugin_data["data"]["plugin"]
    
    # プラグイン名から完全なURLに変換
    plugin_url = f"https://marketplace.dify.ai/plugins/{plugin_name}"
    
    # 更新日時をUTCからJSTに変換
    utc_time = plugin.get("version_updated_at", plugin.get("updated_at", "不明"))
    jst_time = convert_to_jst(utc_time) if utc_time != "不明" else "不明"
    
    return {
        "name": plugin.get("label", {}).get("en_US", plugin.get("name", "不明")),
        "plugin_id": plugin.get("plugin_id", "不明"),
        "latest_version": plugin.get("latest_version", "不明"),
        "version_updated_at": jst_time,
        "version_updated_at_utc": utc_time,  # 元のUTC時間も保持
        "install_count": plugin.get("install_count", 0),
        "url": plugin_url
    }

def fetch_multiple_plugins():
    """
    複数のプラグインから情報を取得し、バージョン情報の要約を出力する関数
    
    環境変数から読み込んだプラグインリストに対して、各プラグインの情報を取得し、
    バージョン情報の要約をログに出力します。
    
    Returns:
        tuple: (results, version_summary)
            - results (list): 各プラグインの生データを含むリスト
            - version_summary (list): 各プラグインのバージョン情報要約を含むリスト
    """
    # 環境変数からプラグインリストを読み込む
    plugin_names = load_plugins_from_env()
    
    logger.info(f"処理するプラグイン数: {len(plugin_names)}")
    results = []
    version_summary = []
    
    for plugin_name in plugin_names:
        logger.info(f"処理中のプラグイン: {plugin_name}")
        plugin_data = fetch_plugin_info(plugin_name)
        if plugin_data:
            # プラグイン情報を結果リストに追加
            results.append({
                "plugin_name": plugin_name,
                "data": plugin_data
            })
            
            # バージョン情報を抽出して要約リストに追加
            version_info = extract_plugin_version_info(plugin_data, plugin_name)
            if version_info:
                version_summary.append(version_info)
    
    # バージョン情報の要約を表示
    if version_summary:
        logger.info("=== プラグインバージョン情報の要約 ===")
        for info in version_summary:
            logger.info(f"プラグイン: {info['name']} ({info['plugin_id']})")
            logger.info(f"  最新バージョン: {info['latest_version']}")
            logger.info(f"  更新日時: {info['version_updated_at']}")
            logger.info(f"  インストール数: {info['install_count']}")
            logger.info("---")
    
    return results, version_summary

def filter_recent_updates(version_summary, hours=1):
    """
    過去指定時間内に更新されたプラグインのみをフィルタリングする関数
    
    現在時刻（UTC）から指定された時間（デフォルト: 1時間）以内に更新された
    プラグインのみを抽出します。更新日時の比較はUTC時間で行われます。
    日時文字列の解析は、マイクロ秒部分の有無や'Z'サフィックスの有無に対応しています。
    
    Args:
        version_summary (list): プラグイン情報のリスト。各要素は辞書で、
                               'version_updated_at_utc'キーに更新日時（UTC）を含む必要があります
        hours (int): 何時間前までの更新を対象とするか（デフォルト: 1時間）
        
    Returns:
        list: 指定時間内に更新されたプラグイン情報のリスト
    
    Note:
        日時変換に失敗した場合はエラーログが出力され、そのプラグインは結果に含まれません
    """
    # 現在時刻（UTC）
    now = datetime.now(timezone.utc)
    # 指定時間前
    time_threshold = now - timedelta(hours=hours)
    logger.info(f"現在時刻(UTC): {now}, 過去{hours}時間の閾値: {time_threshold}")
    
    recent_updates = []
    
    for info in version_summary:
        # UTC時間文字列をdatetimeオブジェクトに変換
        updated_at_str = info.get('version_updated_at_utc')
        if updated_at_str and updated_at_str != "不明":
            try:
                # マイクロ秒部分を含む場合と含まない場合の両方に対応
                if '.' in updated_at_str:
                    if updated_at_str.endswith('Z'):
                        updated_at_str = updated_at_str[:-1]  # 末尾の'Z'を削除
                    updated_at = datetime.fromisoformat(updated_at_str)
                else:
                    # マイクロ秒がない場合
                    if updated_at_str.endswith('Z'):
                        updated_at_str = updated_at_str[:-1]  # 末尾の'Z'を削除
                    updated_at = datetime.fromisoformat(updated_at_str)
                
                # UTCとして扱う
                updated_at = updated_at.replace(tzinfo=timezone.utc)
                
                # 指定時間内に更新されたかチェック
                if updated_at >= time_threshold:
                    recent_updates.append(info)
                    logger.info(f"最近更新されたプラグイン: {info['name']} - {info['version_updated_at']}")
            except Exception as e:
                logger.error(f"日時変換エラー: {e}, 入力: {updated_at_str}")
    
    return recent_updates

def send_to_discord_webhook(recent_updates, webhook_url):
    """
    Discord Webhookに更新情報を送信する関数
    
    更新されたプラグイン情報をDiscord Webhookを使用して通知します。
    各プラグインの情報はEmbedを使用して視覚的に整形されます。
    更新がない場合は通知を送信しません。
    
    Args:
        recent_updates (list): 過去指定時間内に更新されたプラグイン情報のリスト
        webhook_url (str): Discord WebhookのURL
    
    Returns:
        bool: 送信に成功した場合はTrue、失敗した場合はFalse
    """
    # 更新がない場合は通知しない
    if not recent_updates:
        logger.info("最近更新されたプラグインはありません。Discord通知はスキップされます。")
        return True
    
    try:
        # 現在の日時を取得
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Embedのリストを作成
        embeds = []
        
        for info in recent_updates:
            # 各プラグイン情報用のEmbedを作成
            embed = {
                "title": f"{info['name']} ({info['plugin_id']})",
                "url": info['url'],  # プラグインのURLをタイトルにリンクとして設定
                "description": "🔄 **プラグインが更新されました！**",  # 更新された旨を明示的に表示
                "color": 0x5865F2,  # Discordブルー
                "fields": [
                    {
                        "name": "最新バージョン",
                        "value": f"**{info['latest_version']}**",
                        "inline": True
                    },
                    {
                        "name": "更新日時",
                        "value": info['version_updated_at'],
                        "inline": True
                    },
                    {
                        "name": "インストール数",
                        "value": str(info['install_count']),
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"Dify Plugin Update Checker • {current_time}"
                }
            }
            embeds.append(embed)
        
        # 更新されたプラグイン名のリストを作成
        plugin_names = [info['name'] for info in recent_updates]
        plugin_count = len(recent_updates)
        
        # プラグイン名を含むメッセージを作成
        if plugin_count == 1:
            message = f"# Difyプラグイン更新情報: **{plugin_names[0]}** が更新されました"
        else:
            plugins_text = "、".join([f"**{name}**" for name in plugin_names])
            message = f"# Difyプラグイン更新情報: {plugins_text} の{plugin_count}個のプラグインが更新されました"
        
        # Discordのwebhookに送信するデータ
        payload = {
            "content": message,
            "embeds": embeds
        }
        
        # POSTリクエストを送信
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 204:
            logger.info("Discord Webhookへの送信に成功しました")
            return True
        else:
            logger.error(f"Discord Webhookへの送信に失敗しました: ステータスコード {response.status_code}")
            logger.error(f"レスポンス: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Discord Webhook送信中にエラーが発生しました: {e}")
        return False

def send_to_slack_webhook(recent_updates, webhook_url):
    """
    Slack Webhookに更新情報を送信する関数
    
    更新されたプラグイン情報をSlack Webhookを使用して通知します。
    各プラグインの情報はattachmentsを使用して視覚的に整形され、色付けされます。
    更新がない場合は通知を送信しません。
    
    Args:
        recent_updates (list): 過去指定時間内に更新されたプラグイン情報のリスト
        webhook_url (str): Slack WebhookのURL
    
    Returns:
        bool: 送信に成功した場合はTrue、失敗した場合はFalse
    """
    # 更新がない場合は通知しない
    if not recent_updates:
        logger.info("最近更新されたプラグインはありません。Slack通知はスキップされます。")
        return True
    
    try:
        # 現在の日時を取得
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 更新されたプラグイン名のリストを作成
        plugin_names = [info['name'] for info in recent_updates]
        plugin_count = len(recent_updates)
        
        # プラグイン名を含むメッセージを作成
        if plugin_count == 1:
            header_text = f"*Difyプラグイン更新情報*: *{plugin_names[0]}* が更新されました"
        else:
            plugins_text = "、".join([f"*{name}*" for name in plugin_names])
            header_text = f"*Difyプラグイン更新情報*: {plugins_text} の{plugin_count}個のプラグインが更新されました"
        
        # attachmentsのリストを作成
        attachments = []
        color = "#5865F2"
        # ヘッダー用のattachment
        header_attachment = {
            "color": color,
            "pretext": "Difyプラグイン更新情報",
            "text": header_text,
            "footer": f"Dify Plugin Update Checker • {current_time}"
        }
        attachments.append(header_attachment)
        
        # 各プラグイン情報用のattachment
        for info in recent_updates:
            plugin_attachment = {
                "color": color,
                "title": f"{info['name']} ({info['plugin_id']})",
                "title_link": info['url'],
                "text": "🔄 *プラグインが更新されました！*",
                "fields": [
                    {
                        "title": "最新バージョン",
                        "value": info['latest_version'],
                        "short": True
                    },
                    {
                        "title": "更新日時",
                        "value": info['version_updated_at'],
                        "short": True
                    },
                    {
                        "title": "インストール数",
                        "value": str(info['install_count']),
                        "short": True
                    }
                ]
            }
            attachments.append(plugin_attachment)
        
        # Slackのwebhookに送信するデータ
        payload = {
            "attachments": attachments
        }
        
        # POSTリクエストを送信
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 200:
            logger.info("Slack Webhookへの送信に成功しました")
            return True
        else:
            logger.error(f"Slack Webhookへの送信に失敗しました: ステータスコード {response.status_code}")
            logger.error(f"レスポンス: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Slack Webhook送信中にエラーが発生しました: {e}")
        return False

def create_test_plugin_data():
    """
    テスト用のプラグインデータを作成する関数
    
    テストモード用のダミープラグインデータを生成します。
    現在時刻をUTCで取得し、それをJST（日本時間）に変換して使用します。
    
    Returns:
        list: テスト用のプラグイン情報を含むリスト（1つのダミープラグイン）
    """
    current_time = datetime.now(timezone.utc).isoformat()
    
    return [{
        "name": "テスト用プラグイン",
        "plugin_id": "test/plugin",
        "latest_version": "1.0.0",
        "version_updated_at": convert_to_jst(current_time),
        "version_updated_at_utc": current_time,
        "install_count": 123,
        "url": "https://marketplace.dify.ai/plugins/test/plugin"
    }]

def lambda_handler(event, context):
    """
    AWS Lambda関数のエントリーポイント
    
    この関数はAWS Lambdaによって呼び出されるメイン関数です。
    イベントパラメータに基づいて、テストモードまたは通常モードで実行されます。
    
    テストモード（test_slack=True または test_discord=True）では、ダミーデータを使用して
    Slack/Discordへの通知をテストします。
    
    通常モードでは、環境変数から読み込んだプラグインリストの情報を取得し、
    過去1時間以内に更新されたプラグインがあれば通知を送信します。
    
    Args:
        event (dict): Lambda関数に渡されるイベントデータ
            - test_slack (bool): Slackテストモードを有効にするフラグ
            - test_discord (bool): Discordテストモードを有効にするフラグ
        context (LambdaContext): Lambda実行コンテキスト
    
    Returns:
        dict: API Gateway互換のレスポンス
            - statusCode (int): HTTPステータスコード
            - body (str): レスポンスボディ（JSON文字列）
    """
    try:
        # テストモードかどうかをチェック
        test_slack = event.get('test_slack', False)
        test_discord = event.get('test_discord', False)
        
        if test_slack or test_discord:
            logger.info("テストモードが有効です。テスト用のデータを使用します。")
            # テスト用のプラグインデータを作成
            recent_updates = create_test_plugin_data()
            version_summary = recent_updates
            
            # Slack Webhookテスト
            if test_slack:
                logger.info("Slackテストモードが有効です。")
                slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
                if slack_webhook_url:
                    slack_webhook_result = send_to_slack_webhook(recent_updates, slack_webhook_url)
                    logger.info(f"Slackテスト結果: {slack_webhook_result}")
                else:
                    logger.error("SLACK_WEBHOOK_URLが設定されていません。Slackテストはスキップされます。")
                    slack_webhook_result = False
            else:
                slack_webhook_result = False
            
            # Discord Webhookテスト
            if test_discord:
                logger.info("Discordテストモードが有効です。")
                discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
                if discord_webhook_url:
                    discord_webhook_result = send_to_discord_webhook(recent_updates, discord_webhook_url)
                    logger.info(f"Discordテスト結果: {discord_webhook_result}")
                else:
                    logger.error("DISCORD_WEBHOOK_URLが設定されていません。Discordテストはスキップされます。")
                    discord_webhook_result = False
            else:
                discord_webhook_result = False
        else:
            # 通常の処理
            # 環境変数からURLリストを読み込み、データを取得
            _, version_summary = fetch_multiple_plugins()
            
            # 過去1時間以内に更新されたプラグインのみをフィルタリング
            recent_updates = filter_recent_updates(version_summary, hours=1)
            
            # 更新がない場合は明示的にログに出力
            if not recent_updates:
                logger.info("過去1時間以内に更新されたプラグインはありません。")
            
            # Discord Webhookに結果を送信（過去1時間以内の更新のみ）
            # DISCORD_WEBHOOK_URLが設定されている場合のみ実行
            discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
            if discord_webhook_url:
                discord_webhook_result = send_to_discord_webhook(recent_updates, discord_webhook_url)
            else:
                logger.info("DISCORD_WEBHOOK_URLが設定されていません。Discord通知はスキップされます。")
                discord_webhook_result = False
            
            # Slack Webhookに結果を送信（過去1時間以内の更新のみ）
            # SLACK_WEBHOOK_URLが設定されている場合のみ実行
            slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
            if slack_webhook_url:
                slack_webhook_result = send_to_slack_webhook(recent_updates, slack_webhook_url)
            else:
                logger.info("SLACK_WEBHOOK_URLが設定されていません。Slack通知はスキップされます。")
                slack_webhook_result = False
        
        # レスポンスを構築
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'プラグイン情報の取得に成功しました',
                'plugin_data': version_summary,
                'discord_webhook_sent': discord_webhook_result,
                'slack_webhook_sent': slack_webhook_result,
                'test_slack': test_slack,
                'test_discord': test_discord
            }, ensure_ascii=False)
        }
        
        return response
    except Exception as e:
        logger.error(f"エラー: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'エラーが発生しました: {str(e)}'
            }, ensure_ascii=False)
        }