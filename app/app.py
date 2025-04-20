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
    requestsライブラリを使用して指定されたプラグイン名からプラグイン情報を取得し、
    オプションでファイルに保存する関数
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
    環境変数では PLUGINS=plugin1,plugin2,plugin3 の形式で指定
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
    
    Args:
        version_summary: プラグイン情報のリスト
        hours: 何時間前までの更新を対象とするか（デフォルト: 1時間）
        
    Returns:
        list: 指定時間内に更新されたプラグイン情報のリスト
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
    Discord Webhookに結果を送信する関数（Embedを使用）
    recent_updates: 過去指定時間内に更新されたプラグイン情報のリスト
    webhook_url: Discord WebhookのURL
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

def lambda_handler(event, context):
    """
    AWS Lambda関数のエントリーポイント
    """
    try:
        # 環境変数からURLリストを読み込み、データを取得
        _, version_summary = fetch_multiple_plugins()
        
        # 過去1時間以内に更新されたプラグインのみをフィルタリング
        recent_updates = filter_recent_updates(version_summary, hours=1)
        
        # 更新がない場合は明示的にログに出力
        if not recent_updates:
            logger.info("過去1時間以内に更新されたプラグインはありません。")
        
        # Discord Webhookに結果を送信（過去1時間以内の更新のみ）
        # DISCORD_WEBHOOK_URLが設定されている場合のみ実行
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if webhook_url:
            webhook_result = send_to_discord_webhook(recent_updates, webhook_url)
        else:
            logger.info("DISCORD_WEBHOOK_URLが設定されていません。Discord通知はスキップされます。")
            webhook_result = False
        
        # レスポンスを構築
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'プラグイン情報の取得に成功しました',
                'plugin_data': version_summary,
                'discord_webhook_sent': webhook_result
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