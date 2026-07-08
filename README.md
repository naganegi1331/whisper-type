# WhisperType

**Windows 向け AI リアルタイム音声入力アプリ**

WhisperType は「Windows で iPhone のような快適な音声入力を実現する」ことを目的とした AI 音声入力アプリケーションです。

ホットキー（既定: `Ctrl + Shift + Space`）を押すだけで音声入力を開始でき、話した内容はリアルタイムに文字へ変換され、**現在カーソルがあるアプリケーションへ自動入力**されます。

- 🖥️ システムトレイに常駐し、Windows 上のあらゆるアプリから利用可能
- 🔒 音声認識はすべて**ローカル PC 上**で実行（whisper.cpp / large-v3-turbo）。音声データを外部へ送信しません
- 📡 オフラインで利用可能（モデル配置済みの場合）
- 🇯🇵 日本語・英語に対応

## 動作環境

| 項目 | 内容 |
|---|---|
| OS | Windows 11 |
| Python | 3.11 以上 |
| GUI | PySide6 |
| 音声認識 | whisper.cpp（pywhispercpp 経由） |
| モデル | large-v3-turbo |

## セットアップ

### 1. 依存ライブラリのインストール

```powershell
git clone https://github.com/naganegi1331/whisper-type.git
cd whisper-type
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Whisper モデルの配置

large-v3-turbo モデル（約 1.6 GB）をダウンロードし、`models/` フォルダへ配置します。

```powershell
curl -L -o models/ggml-large-v3-turbo.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

モデルの配置場所は設定画面（モデルファイル）から変更できます。

### 3. 起動

```powershell
python -m whispertype
```

起動するとシステムトレイに常駐します。トレイアイコンを左クリックするとメイン画面が表示されます。

## 使い方

1. 文字を入力したいアプリ（メモ帳・Word・Teams・ブラウザーなど）にカーソルを置く
2. `Ctrl + Shift + Space` を押す → 音声入力開始（トレイアイコンが赤に変化）
3. 話す → 認識結果がリアルタイムにカーソル位置へ入力される
4. もう一度 `Ctrl + Shift + Space` を押す → 音声入力停止

### メイン画面

```
----------------------------------------------------
WhisperType
Status    🟢 待機中
Model     large-v3-turbo
Hotkey    Ctrl + Shift + Space
☑ Auto Input
----------------------------------------------------
Recognized Text
（認識結果がここに表示されます）
----------------------------------------------------
[Start]  [Stop]  [Settings]
----------------------------------------------------
```

### 設定項目

| 設定 | 説明 |
|---|---|
| ホットキー | 音声入力の開始/停止キー（既定 `ctrl+shift+space`） |
| 自動入力 ON/OFF | カーソル位置への自動入力の有効/無効 |
| 自動入力開始までの待機時間 | 認識開始から入力開始までの遅延（ms） |
| 入力速度 | 1 文字あたりの入力間隔（0 = 最速） |
| 認識言語 | 自動判定 / 日本語 / 英語 |
| モデルファイル | whisper.cpp 用モデル（ggml/gguf）のパス |
| 自動起動 | Windows 起動時に自動常駐 |

設定は `%APPDATA%\WhisperType\config.json` に保存されます。

## アーキテクチャ

```
マイク → sounddevice（音声取得 16kHz/mono）
       → StreamingRecognizer（一定間隔で途中認識）
       → whisper.cpp large-v3-turbo（ローカル実行）
       → AutoTypist（差分計算 → pynput でカーソル位置へ入力）
```

- 途中認識結果は入力済みテキストとの**共通接頭辞差分**で追従します（訂正は Backspace で自動修正）
- 発話が長くなった場合（25 秒超）は区間を確定し、続きを新しい区間として認識します
- GPU 対応版の pywhispercpp（CUDA / Vulkan ビルド）を導入すると、コード変更なしで GPU を活用できます

主なモジュール:

| モジュール | 役割 |
|---|---|
| `whispertype/audio.py` | マイク録音（sounddevice） |
| `whispertype/engine.py` | whisper.cpp エンジン（pywhispercpp） |
| `whispertype/recognizer.py` | ストリーミング認識ループ |
| `whispertype/textdiff.py` | 途中結果の差分計算 |
| `whispertype/typist.py` | 自動入力（pynput） |
| `whispertype/hotkey.py` | グローバルホットキー（keyboard） |
| `whispertype/controller.py` | 全体制御・状態管理 |
| `whispertype/gui/` | メイン画面・設定・トレイ（PySide6） |

## 開発

```powershell
pip install pytest
python -m pytest
```

コアロジック（差分計算・設定・認識ループ・状態遷移）は GUI・音声デバイス非依存で、Windows 以外の環境でもテストできます。

## ドキュメント

- [要件定義書（Ver.1.0）](docs/requirements.md)

## ライセンス

MIT License
