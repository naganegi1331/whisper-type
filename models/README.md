# models/

whisper.cpp 用の Whisper モデルファイルをこのフォルダへ配置してください。

既定のモデル: **large-v3-turbo**

```powershell
curl -L -o models/ggml-large-v3-turbo.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

- ファイルサイズは約 1.6 GB です
- モデルファイル（*.bin / *.gguf）は `.gitignore` によりリポジトリへはコミットされません
- 別の場所に置く場合は、設定画面の「モデルファイル」でパスを指定してください
