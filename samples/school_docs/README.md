# 学校配布物サンプル画像

学校配布物スキャン機能のテスト用画像置き場。
（画像ファイルは .gitignore で除外されているため、Git には含まれない）

## 使い方

```bash
# サンプル画像でアップロードテスト
curl -X POST http://localhost:8080/api/school-docs/upload \
  -H "Authorization: Bearer <API_TOKEN>" \
  -F "child_name=紗奈" \
  -F "file=@samples/school_docs/IMG_8087.PNG"
```

## 注意
実際の配布物画像は個人情報を含むため、Git にコミットしないこと。
