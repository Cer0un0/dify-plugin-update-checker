# Dify Plugin Update Checker

Dify Marketplaceのプラグイン更新を自動的に監視し、更新があった場合にDiscord通知を送信するAWS Lambda関数です。

## 概要

このプロジェクトは、[Dify](https://dify.ai)のMarketplaceで公開されているプラグインの更新を定期的にチェックし、新しいバージョンがリリースされた場合にDiscord Webhookを通じて通知します。AWS SAM（Serverless Application Model）を使用して、AWS Lambda上にデプロイされるサーバーレスアプリケーションとして実装されています。

## 主な機能

- 指定したDifyプラグインの最新バージョン情報を自動取得
- 過去1時間以内に更新されたプラグインを検出
- 更新があった場合、Discord Webhookを通じて通知
- 1時間ごとに自動実行（CloudWatch Eventsによるスケジュール実行）

## 設定方法

### 環境変数

Lambda関数は以下の環境変数を使用します：

- `PLUGINS`: 監視対象のプラグインリスト（カンマ区切り）
  - 例: `langgenius/openai,langgenius/anthropic,langgenius/gemini`
  - フォーマット: `{組織名}/{プラグイン名}`
- `DISCORD_WEBHOOK_URL`: 通知先のDiscord WebhookのURL
  - 空の場合、Discord通知は送信されません

これらの環境変数は`template.yaml`ファイル内で設定できます。

## デプロイ方法

### 前提条件

- [AWS CLI](https://aws.amazon.com/cli/)
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- [Python 3.12](https://www.python.org/downloads/)
- [Docker](https://www.docker.com/products/docker-desktop) (ローカルテスト用)

### デプロイ手順

1. リポジトリをクローン

```bash
git clone https://github.com/yourusername/dify-plugin-update-checker.git
cd dify-plugin-update-checker
```

2. `template.yaml`ファイルを編集して、環境変数を設定

```yaml
Environment:
  Variables:
    PLUGINS: "langgenius/openai,langgenius/anthropic,langgenius/gemini,langgenius/azure_openai,langgenius/cohere,langgenius/bedrock,langgenius/ollama"
    DISCORD_WEBHOOK_URL: "あなたのDiscord WebhookのURL"
```

3. SAMを使用してビルドとデプロイを実行

```bash
sam build --use-container
sam deploy --guided
```

デプロイ時に以下の情報を入力します：

- **Stack Name**: スタック名（例: `dify-plugin-update-checker`）
- **AWS Region**: デプロイするリージョン（例: `ap-northeast-1`）
- **Confirm changes before deploy**: 変更を確認するか（推奨: `Y`）
- **Allow SAM CLI IAM role creation**: IAMロールの作成を許可するか（`Y`）
- **Save arguments to samconfig.toml**: 設定を保存するか（`Y`）

## ローカルでのテスト

SAM CLIを使用してローカルでLambda関数をテストできます：

```bash
# ビルド
sam build --use-container

# ローカル実行
sam local invoke DifyPluginCheckerFunction
```

## 更新通知の例

更新が検出された場合、以下のような通知がDiscordに送信されます：

- プラグイン名とID
- 最新バージョン
- 更新日時（日本時間）
- インストール数
- Dify Marketplaceへのリンク

## ログの確認

CloudWatch Logsでログを確認できます：

```bash
sam logs -n DifyPluginCheckerFunction --stack-name "dify-plugin-update-checker" --tail
```

## リソースの削除

不要になった場合は、以下のコマンドでリソースを削除できます：

```bash
sam delete --stack-name "dify-plugin-update-checker"
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
