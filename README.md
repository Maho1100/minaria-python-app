# Minaria Static

Minaria Static は、プログラミング初学者向けの  
**完全クライアントサイド型・学習ゲーム教材**です。

ブラウザで URL を開くだけで学習を開始でき、  
サーバー起動やログインを必要としません。

---

## 特徴

- ブラウザのみで動作（サーバーレス）
- 問題データは JSON ファイルで管理
- 学習進捗は localStorage に保存
- GitHub Pages で公開可能
- スマホ・PC 両対応

---

## 公開URL

- Home  
  https://maho1100.github.io/minaria-static/

- Stage1  
  https://maho1100.github.io/minaria-static/#/stage1

---

## 対象ユーザー

- プログラミング初学者
- 小学生〜中学生
- 教育者・保護者による利用も想定

---

## 使い方（学習者）

1. 上記URLをブラウザで開く
2. Stageを選択
3. 問題に答える
4. 正解すると XP が増える
5. 進捗は自動保存される（次回も続きから）

※ 学習データは利用者の端末内にのみ保存されます。

---

## 開発者向け

### ローカル起動

```bash
npm install
npm run dev
