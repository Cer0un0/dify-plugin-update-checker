import argparse
import json
import logging
import os
import sys
from pathlib import Path

import requests  # curlの代わりにrequestsを使用
from dotenv import load_dotenv

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def fetch_plugin_info(url):
    """
    requestsライブラリを使用して指定されたURLからプラグイン情報を取得し、
    オプションでファイルに保存する関数
    """
    try:
        # URLからプラグインのパスを抽出
        # 例: https://marketplace.dify.ai/plugins/langgenius/openai → langgenius/openai
        plugin_path = url.split('/plugins/')[1] if '/plugins/' in url else url
        
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

def load_urls_from_env():
    """
    .envファイルからURLリストを読み込む関数
    .envファイル内では PLUGIN_URLS=url1,url2,url3 の形式で指定
    """
    # .envファイルを読み込む
    env_path = Path('.') / '.env'
    if not env_path.exists():
        raise FileNotFoundError(".envファイルが見つかりません。.envファイルを作成してください。")
    
    load_dotenv()
    
    # PLUGIN_URLS環境変数を取得
    plugin_urls = os.getenv('PLUGIN_URLS')
    if not plugin_urls:
        raise ValueError("PLUGIN_URLSが.envファイルに設定されていません。.envファイルにPLUGIN_URLSを設定してください。")
    
    # カンマ区切りのURLリストを分割
    urls = [url.strip() for url in plugin_urls.split(',')]
    logger.info(f".envファイルから{len(urls)}個のURLを読み込みました")
    return urls

def extract_plugin_version_info(plugin_data):
    """
    プラグインデータから重要なバージョン情報を抽出する関数
    """
    if not plugin_data or "data" not in plugin_data or "plugin" not in plugin_data["data"]:
        return None
    
    plugin = plugin_data["data"]["plugin"]
    
    return {
        "name": plugin.get("label", {}).get("en_US", plugin.get("name", "不明")),
        "plugin_id": plugin.get("plugin_id", "不明"),
        "latest_version": plugin.get("latest_version", "不明"),
        "version_updated_at": plugin.get("version_updated_at", plugin.get("updated_at", "不明")),
        "install_count": plugin.get("install_count", 0)
    }

def fetch_multiple_plugins():
    """
    複数のプラグインURLから情報を取得し、バージョン情報の要約を出力する関数
    """
    # .envファイルからURLリストを読み込む
    urls = load_urls_from_env()
    
    logger.info(f"処理するURL数: {len(urls)}")
    results = []
    version_summary = []
    
    for url in urls:
        logger.info(f"処理中のURL: {url}")
        plugin_data = fetch_plugin_info(url)
        if plugin_data:
            # プラグイン情報を結果リストに追加
            results.append({
                "url": url,
                "data": plugin_data
            })
            
            # バージョン情報を抽出して要約リストに追加
            version_info = extract_plugin_version_info(plugin_data)
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
    
    # バージョン情報の要約をJSONファイルに保存
    if version_summary:
        summary_file = "output_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(version_summary, indent=2, ensure_ascii=False, fp=f)
        logger.info(f"バージョン情報の要約を {summary_file} に保存しました")
    
    return results, version_summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Dify.aiのプラグイン情報を取得するスクリプト')
    args = parser.parse_args()
    
    try:
        # .envファイルからURLリストを読み込み、データを取得
        _, _ = fetch_multiple_plugins()
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"エラー: {e}")
        sys.exit(1)