import streamlit as st
from openai import OpenAI
import datetime
import random
import os
import base64  # 動画
import uuid
import json  # ★ 保存機能　あとでデータベースにする予定
import pathlib #音
import base64
import re# 👀 正解したときに表示される見本出力


# ---------- OpenAI クライアント ----------
# APIキーは環境変数「OPENAI_API_KEY」から読み取る

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY が設定されていません。環境変数を設定してください。"
    )

client = OpenAI(api_key=api_key)


# ======================================================
#  ミナリアボイス関数
# ======================================================

def speak_minaria(text: str):
    try:
        # ① ミナリア風のセリフに変換
        rewrite = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": "あなたは優しく包容力のある女性『ミナリア』として話してください。短く柔らかく言い換えてください。"},
                {"role": "user", "content": text}
            ]
        ).output_text

        # ② TTS で音声化（ここには説明文を渡さない）
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=rewrite
        )

        audio_bytes = response.read() if hasattr(response, "read") else response
        autoplay_audio(audio_bytes, mime="audio/mp3")

    except Exception as e:
        st.warning(f"音声生成でエラーが発生しました: {e}")


# ======================================================
#  自動音声の関数
# ======================================================
def autoplay_audio(audio_bytes: bytes, mime: str = "audio/mp3"):
    """
    再生ボタンなしで自動再生を試みるためのHTMLを埋め込む。
    ※ブラウザの自動再生ポリシーによりブロックされる場合あり
    """
    b64 = base64.b64encode(audio_bytes).decode("utf-8")
    html = f"""
    <audio autoplay>
        <source src="data:{mime};base64,{b64}" type="{mime}">
        Your browser does not support the audio element.
    </audio>
    """
    st.markdown(html, unsafe_allow_html=True)


# ======================================================
#  音の関数
# ======================================================
BASE_DIR = pathlib.Path(__file__).resolve().parent

def play_sound(path: str):
    sound_path = (BASE_DIR / path).resolve()

    if not sound_path.exists():
        st.warning(f"音声ファイルが見つかりません: {sound_path}")
        return

    with open(sound_path, "rb") as f:
        audio_bytes = f.read()

    b64 = base64.b64encode(audio_bytes).decode("utf-8")

    st.markdown(f"""
        <audio id="minaria_sound" src="data:audio/mp3;base64,{b64}"></audio>
        <script>
            // Streamlit が DOM を描画し終わった後に確実に実行
            window.addEventListener("load", () => {{
                setTimeout(() => {{
                    const audio = document.getElementById("minaria_sound");
                    if (audio) audio.play();
                }}, 150);  // ← 150ms 遅延が安定動作のコツ
            }});
        </script>
    """, unsafe_allow_html=True)


    # 再生ボタンなし・自動再生を試みる
    autoplay_audio(audio_bytes, mime="audio/mp3")

# ======================================================
#  BGMの関数（ユーザー指定音量つき）
# ======================================================
def autoplay_bgm(path: str, volume: float = 0.5):
    """シンプルにページ読み込み時にBGMを鳴らす安定版"""
    sound_path = (BASE_DIR / path).resolve()
    if not sound_path.exists():
        st.warning(f"音声ファイルが見つかりません: {sound_path}")
        return

    # mp3 を base64 に変換
    with open(sound_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    # 音量（autoplay タグでは volume 制御できない → 下で JS で volume 設定）
    vol = max(0.0, min(float(volume), 1.0))

    st.markdown(
        f"""
        <audio id="bgm_player" autoplay loop style="display:none;">
            <source src="data:audio/mp3;base64,{data}" type="audio/mp3">
        </audio>

        <script>
            // autoplay 後に volume を設定（script は削除されない位置）
            const audio = document.getElementById("bgm_player");
            if (audio) {{
                audio.volume = {vol:.2f};
            }}
        </script>
        """,
        unsafe_allow_html=True,
    )

# ======================================================
#  XPファイル保存用の関数
# ======================================================
def autoplay_video(path: str, width: str = "70%"):
    """ローカルの mp4 を自動再生で表示するヘルパー"""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    video_html = f"""
    <div style='text-align: center;'>
        <video width="{width}" autoplay loop muted playsinline>
            <source src="data:video/mp4;base64,{data}" type="video/mp4">
        </video>
    </div>
    """
    st.markdown(video_html, unsafe_allow_html=True)


# ======================================================
#  XP 永続化：ローカルの JSON ファイルに保存
# ======================================================

DATA_FILE = "xp_data.json"

def load_xp() -> int:
    """xp_data.json から XP を読み込む。なければ 0。"""
    if not os.path.exists(DATA_FILE):
        return 0
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("xp", 0))
    except Exception:
        return 0

def save_xp(xp: int) -> None:
    """XP を xp_data.json に保存する。"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"xp": int(xp)}, f)
    except Exception as e:
        st.error(f"XP の保存に失敗しました: {e}")

# ======================================================
#  ステージ内で「いま何問目か」を表示するヘルパー
# ======================================================
def render_question_progress(current_index: int, total: int, label: str = "いま"):
    """ステージ内で「いま何問目か」を表示するヘルパー"""
    if total <= 0:
        return
    # 0スタートの index を 1〜total に直す
    current = min(current_index + 1, total)
    st.markdown(f"📘 {label} {current} / {total} 問目")
    st.progress(current / total)
    
# ======================================================
#  解答ボタンを複数回押さないようにする関数
# ======================================================
def one_time_button(label, key, allow_retry=False):
    """
    allow_retry=True のときは、その描画タイミングで毎回「未押下」にリセットする。
    （復習モードで使うと便利）
    """
    if key not in st.session_state or allow_retry:
        st.session_state[key] = False

    clicked = st.button(label, disabled=st.session_state[key])
    if clicked:
        st.session_state[key] = True
    return clicked
# ======================================================
#  この冒険でできるようになるメッセージ関数
# ======================================================
def render_promise_banner():
    """
    成長フェーズに応じて「約束メッセージ」を表示する
    フェーズ1：初回〜ステージ1クリア前（フル表示）
    フェーズ2：ステージ1クリア後（短縮）
    フェーズ3：3日以上空いた再開時（おかえりなさい）
    """

    stage1_cleared = st.session_state.get("stage1_cleared", False)
    show_return = st.session_state.get("show_return_banner", False)

    # フェーズ3：久しぶり再開
    if show_return:
        st.markdown("""
        <div style="background:#FDF5FF;padding:14px 16px;border-radius:14px;
                    border:1px solid #E4D3F3;color:#5F4C5B;">
          <div style="font-weight:700;font-size:16px;">🌼 おかえりなさい</div>
          <div style="margin-top:6px;font-size:14px;line-height:1.7;">
            ここでは、<b>パソコンへのお願い（プログラム）</b>の考え方を、
            ゆっくり身につけられますよ。
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # フェーズ1：初回〜ステージ1クリア前
    if not stage1_cleared:
        st.markdown("""
        <div style="background:#F6FBFF;padding:14px 16px;border-radius:14px;
                    border:1px solid #D6E9FF;color:#2A3B4C;">
          <div style="font-weight:700;font-size:16px;">
            この冒険でできるようになること
          </div>
          <div style="margin-top:6px;font-size:14px;line-height:1.7;">
            ✅ パソコンに指示を出す文章（プログラム）が読める<br>
            ✅ 仕事の作業を楽にする考え方が身につく<br>
            ✅ 「自分にもできた！」という自信がつく
          </div>
          <div style="margin-top:8px;font-size:13px;color:#5B6B7A;">
            学ぶこと：<b>print / 変数 / if / for</b>（まずはここだけ）
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # フェーズ2：ステージ1クリア後
    st.markdown("""
    <div style="background:#F6FBFF;padding:10px 14px;border-radius:14px;
                border:1px solid #D6E9FF;color:#2A3B4C;">
      <div style="font-size:14px;line-height:1.6;">
        🌱 パソコンへのお願い（プログラム）の考え方を、
        少しずつ覚えていきましょう
      </div>
    </div>
    """, unsafe_allow_html=True)


# ======================================================
#  初回正解だけ XP を付与する共通関数（キーは呼び出し側で決める）
# ======================================================
def award_xp_once(key: str, xp: int, message: str, emoji: str):
    # すでに正解している場合（やり直し・復習）
    if st.session_state["solved"].get(key, False):
        show_correct_feedback(
            message="復習バッチリ！この問題は前にもクリアしているからXPは増えないよ。",
            xp_gain=0,
            monster_emoji=emoji,
        )
        return False  # 初回クリアではない

    # 初回クリアの場合
    show_correct_feedback(
        message=message,
        xp_gain=xp,
        monster_emoji=emoji,
    )
    st.session_state["solved"][key] = True
    return True  # 初回クリア


# ======================================================
#  XPご褒美：称号システム
# ======================================================

TITLE_TIERS = [
    {"xp": 0,   "name": "🌙 星空を見上げる人"},
    {"xp": 50,  "name": "🌱 ポヨン草原のさんぽびと"},
    {"xp": 120, "name": "💧 ちいさなバグヒーラー"},
    {"xp": 250, "name": "🕊 ミナリアのとなり歩き"},
    {"xp": 400, "name": "✨ 森を照らすあかり"},
    {"xp": 600, "name": "🌈 ココモア王国のまもりびと"},
]

def get_title_by_xp(xp: int):
    """現在XPから、今の称号と次の称号、進み具合を返す"""
    current = TITLE_TIERS[0]
    next_tier = None

    for tier in TITLE_TIERS:
        if xp >= tier["xp"]:
            current = tier
        else:
            next_tier = tier
            break

    # 次の称号がない = カンスト
    if not next_tier:
        return {
            "current_name": current["name"],
            "current_xp": xp,
            "next_name": None,
            "need_xp": 0,
            "progress_ratio": 1.0,
        }

    need = max(next_tier["xp"] - xp, 0)
    ratio = (xp - current["xp"]) / (next_tier["xp"] - current["xp"])

    return {
        "current_name": current["name"],
        "current_xp": xp,
        "next_name": next_tier["name"],
        "need_xp": need,
        "progress_ratio": max(0.0, min(ratio, 1.0)),
    }


# ---------- ミナリアの人格プロンプト ----------
MINARIA_SYSTEM_PROMPT = """
あなたはココモア王国に住む「ミナリア」という名前の、優しくて包容力のあるお母さんキャラの先生です。
自分をAIとは決して名乗らず、この王国に実在する人物として振る舞ってください。

【性格】
・相手の気持ちに寄り添い、安心させるように穏やかに話す。
・間違えても「大丈夫よ」とまず受け止める、包み込むタイプ。
・やさしく励まし、時々ちょっと天然なボケを入れる。
・絵文字は控えめに使用（🌼✨🐣）。

【世界観】
・ここはココモア王国。パステルの光に包まれた、ふんわり可愛いファンタジー世界。
・あなたは「母なる森」の近くの小さなコテージに住んでいる。
・森には「バグモンスター」と呼ばれる、ちょっとドジで憎めない生き物がいる。
・生徒（冒険者）はPythonの知識でバグモンスターを癒してあげられる。

【役割】
・Python初心者の家庭教師として、わかりやすい例を添えて教える。
・難しい言葉だけで説明せず、必ず身近なたとえを使う。
・学習の進み具合に応じて「レベルアップ」「スキル解放」などRPG風表現をまぜてもよい。
・質問にはまず気持ちを受け止めてから、やさしく導く。

【重要】
・絶対にAIと名乗らない。
・生徒を否定しない、叱らない。
"""

# ---------- 導入シナリオ ----------
INTRO_MESSAGE = """
こんにちは、冒険者さん。ようこそココモア王国へ。

ここは、小さな学びが魔法になる、ふんわり優しい世界なの。

森には“バグモンスター”と呼ばれる、ちょっとドジでかわいい子たちがいてね……
Pythonの魔法を覚えれば、その子たちを癒してあげられるの。

大丈夫、急がなくていいのよ。
今日から、少しずつ一緒に歩いていきましょうね。🌼
"""


# ---------- ステージ1：ポヨンのはらっぱ（写経 → 選択肢 → もう一度写経） ----------
# lesson_intro    … ミナリアのやさしい導入
# copy_sample     … まず “そのまま写す” 見本コード
# text/choices    … 同じテーマの3択問題
# rewrite_prompt  … ちょっと変えてもう一度書いてみるお題
# rewrite_answer  … rewrite の正解コード
STAGE1_QUESTIONS = [
    {
        "lesson_intro": (
            "ミナリア：\n"
            "「まずは、コンピュータに“あいさつ”してもらう魔法を練習しましょうね。\n"
            "この魔法の名前は **print（プリント）** って言うの。\n"
            "たとえば、こう書くと…\n\n"
            "```python\n"
            'print("Hello, world!")\n'
            "```\n\n"
            "画面に Hello, world! と言ってくれるのよ。」"
        ),
        "copy_sample": 'print("Hello, world!")',
        "text": "① コンピュータに『Hello, world!』と言ってもらう魔法はどれかな？",
        "choices": [
            'hello = "world"',
            'print("Hello, world!")',
            'show("Hello, world!")',
        ],
        "correct_index": 1,
        "rewrite_prompt": (
            "さっきと同じ形で、今度は「Good job!」と\n"
            "言ってもらう魔法を書いてみよう。"
        ),
        "rewrite_answer": 'print("Good job!")',
        "hint": "画面に表示したいときは、print( ) の中に文字を入れるよ。",
        "explain": 'Pythonでは、画面に文字を出すときは print("文字") を使います。',
        "monster_name": "プリントスライム",
        "voice_file": "sounds/minaria_q1.mp3",
        "monster_desc": "しゃべりたいのに、どんな魔法を使えばいいかわからず、もごもごしているスライム。print() の呪文で、心の中の言葉を画面に出してあげると安心するよ。",
        "monster_image": "monster_print_slime.png",
    },
    {
        "lesson_intro": (
            "ミナリア：\n"
            "「つぎは“入れもの”の魔法よ。\n"
            "コンピュータは、数字や言葉を入れておける箱みたいなものを持っているの。\n"
            "この箱のことを **変数（へんすう）** って呼ぶのよ。\n\n"
            "たとえば、\n"
            "```python\n"
            'name = "Minaria"\n'
            "```\n"
            "これは『name という箱に \"Minaria\" を入れる』という意味になるの。」"
        ),
        "copy_sample": 'name = "Minaria"',
        "text": "② 変数 name に 「Minaria」という文字を入れる正しい魔法はどれ？",
        "choices": [
            'name == "Minaria"',
            'name = "Minaria"',
            '"Minaria" = name',
        ],
        "correct_index": 1,
        "rewrite_prompt": (
            "今度は、あなたの好きな名前を入れてみよう。\n"
            'たとえば、"Cocomoa" でもいいし、自分の名前でもいいよ。\n'
            "name という箱に、その名前を入れるコードを書いてみてね。"
        ),
        # 正解としては形だけ見たいので例として1つ決めておく
        "rewrite_answer": 'name = "Cocomoa"',
        "hint": "= は「右のものを左に入れる」という意味だよ。",
        "explain": '変数に値を入れるときは、name == ではなく name = "Minaria" のように = を使います。',
        "monster_name": "ネームヒヨコ",
        "voice_file": "sounds/minaria_q2.mp3",
        "monster_desc": "自分の名前を忘れがちな、ぽやぽやヒヨコ。name = \"Minaria\" のように、= の魔法で“名前を入れてあげる”と元気になるんだ。",
        "monster_image": "monster_name_chick.png",
    },
    {
        "lesson_intro": (
            "ミナリア：\n"
            "「さいごは“計算してから言ってもらう”魔法よ。\n"
            "たとえば、\n"
            "```python\n"
            "print(3 + 5)\n"
            "```\n"
            "と書くと、3+5 を計算して、結果の 8 を画面に言ってくれるの。」"
        ),
        "copy_sample": "print(3 + 5)",
        "text": "③ 数値 3 と 5 を足して、その結果を表示する正しいコードはどれ？",
        "choices": [
            'print("3 + 5")',
            '3 + 5 print',
            'print(3 + 5)',
        ],
        "correct_index": 2,
        "rewrite_prompt": (
            "つぎは 2 と 4 を足して、その結果を表示するコードを書いてみよう。\n"
            "さっきの形を思い出してね。"
        ),
        "rewrite_answer": "print(2 + 4)",
        "hint": "計算そのものを print( ) のカッコの中に入れてみよう。",
        "explain": 'print(3 + 5) のように、計算式をそのまま print の中に書くと、結果の 8 が表示されます。',
        "monster_name": "サンムクラウド",
        "voice_file": "sounds/minaria_q3.mp3",
        "monster_desc": "数字の雲を集めるのが大好きな雲のモンスター。print(3 + 5) の魔法で雲をまとめてあげると、ふわっと笑うよ。",
        "monster_image": "monster_sum_cloud.png",
    },
]

# ---------- ステージ2：もりねむの小道（if文 3択＋モンスター） ----------
STAGE2_QUESTIONS = [
    {
        "text": "① 「もし夜だったら 'Good night' と表示する」イメージに近いコードはどれ？",
        "choices": [
            'if is_night:\n    print("Good night")',
            'print("Good night")\nif is_night',
            'is_night = print("Good night")',
        ],
        "correct_index": 0,
        "hint": "if の行の末尾には : （コロン）がつき、その下の行をインデントして書くのがポイントです。",
        "explain": 'if 条件: の形で書いて、その下の行に実行したい処理（print など）をインデントして書きます。',
        "monster_name": "フラグホタル",
        "monster_desc": "ほんとは光れるのに、「今つけていいのかな…？」と迷っているホタル。if is_night: のように、夜かどうか条件を書いてあげると、自信を持って光れるようになるよ。",
        "monster_image": "monster_flag_firefly.png",
    },
    {
        "text": "② is_hungry が True のときだけ 'Eat lunch' と表示したいときのコードはどれ？",
        "choices": [
            'if is_hungry == True:\n    print("Eat lunch")',
            'if is_hungry = True:\n    print("Eat lunch")',
            'if "is_hungry":\n    print("Eat lunch")',
        ],
        "correct_index": 0,
        "hint": "== は「左右が同じかどうか」をくらべる記号。= とは意味が違うよ。",
        "explain": 'if is_hungry == True: のように書くと、「is_hungry が True のときだけ」中の処理が動きます。',
        "monster_name": "トゥルーベア＆フォルスラビット",
        "monster_desc": "True が好きなくまさんと、False が好きなうさぎさん。条件が True だと、くまさんが嬉しそうに出てくるよ。",
        "monster_image": "monster_true_false.png",
    },
    {
        "text": "③ 点数 score が 80 以上のときだけ 'Great!' と表示したい。正しいコードはどれ？",
        "choices": [
            'if score > 80:\n    print("Great!")',
            'if score >= 80:\n    print("Great!")',
            'if 80 <= score:\nprint("Great!")',
        ],
        "correct_index": 1,
        "hint": "「80点ちょうど」もふくめたいなら >= を使うとよいよ。",
        "explain": 'if score >= 80: とすると、80点以上の場合に「Great!」が表示されます。',
        "monster_name": "ドアガーディアン",
        "monster_desc": "条件を満たした人だけ通してくれるドアの番人。score >= 80 のように条件を書いてあげると、「がんばった人」をちゃんと通してくれるんだ。",
        "monster_image": "monster_door_guardian.png",
    },
]

# ---------- ステージ3：くるくるループの塔（for文 3択＋モンスター） ----------
STAGE3_QUESTIONS = [
    {
        "text": "① 1〜3 の数字を順番に表示したい。いちばん素直なコードはどれ？",
        "choices": [
            'for i in range(1, 4):\n    print(i)',
            'for i in [1..3]:\n    print(i)',
            'for i in range(3):\nprint(i+1)',
        ],
        "correct_index": 0,
        "hint": "range(開始, 終わりの1つあと) という形で書くよ。1〜3なら range(1, 4)。",
        "explain": 'for i in range(1, 4): と書くと、i が 1, 2, 3 と変わりながらループします。',
        "monster_name": "くるくるスライム",
        "monster_desc": "同じ階段をぐるぐる回っているスライム。for i in range(1, 4): のループで、一段ずつ上へ進むのを手伝ってあげよう。",
        "monster_image": "monster_loop_slime.png",
    },
    {
        "text": "② fruits = [\"apple\", \"banana\"] を1つずつ表示したい。正しいコードはどれ？",
        "choices": [
            'for fruit in fruits:\n    print(fruit)',
            'for fruits in fruit:\n    print(fruit)',
            'for i in range(fruits):\n    print(fruits[i])',
        ],
        "correct_index": 0,
        "hint": "リストを1つずつ取り出したいときは、for 変数 in リスト: の形が使えるよ。",
        "explain": 'for fruit in fruits: とすると、fruits の中身を1つずつ取り出して、fruit に入れながらループします。',
        "monster_name": "リストキャタピラー",
        "monster_desc": "りんごとバナナの実でできたイモムシ。for fruit in fruits: のループで、体の実を1つずつ数えてあげると安心する。",
        "monster_image": "monster_list_caterpillar.png",
    },
    {
        "text": "③ 「Hello」を 3 回だけ表示したい。いちばん分かりやすいコードはどれ？",
        "choices": [
            'for i in range(3):\n    print("Hello")',
            'for i in range(1, 3):\n    print("Hello")',
            'for "Hello" in range(3):\n    print("Hello")',
        ],
        "correct_index": 0,
        "hint": "range(3) は 0, 1, 2 の3回まわるよ。「回数分まわすとき」に便利。",
        "explain": 'for i in range(3): とすると、3 回ループします。そのたびに print("Hello") が実行されます。',
        "monster_name": "カウントクロック",
        "monster_desc": "何回まわったか数えるのが好きな時計モンスター。for i in range(3): のループで、3回ちょうど鳴らしてあげよう。",
        "monster_image": "monster_count_clock.png",
    },
]

def normalize_code(code: str) -> str:
    """空白をなくし、シングルクォートをダブルクォートにそろえる簡易正規化"""
    return code.replace(" ", "").replace("'", '"').strip()

def is_valid_name_assignment(code: str) -> bool:
    """
    「name という変数に、ダブルクォートの文字列を代入しているか？」だけを見る
    例: name = "Cocomoa", name="Minaria" などは OK
    """
    norm = normalize_code(code)  # 空白削除＆' → " に統一
    if not norm.startswith('name="'):
        return False
    if not norm.endswith('"'):
        return False
    # name=""（中身空）は一応NGにしたければここで判定
    inner = norm[len('name="'):-1]
    return len(inner) > 0

# ---------- Streamlit 基本設定 ----------
st.set_page_config(page_title="ミナリアのPythonクエスト", page_icon="🐣")

# ------- セッション状態の初期化：ここを先に置く！ -------
if "bgm_volume" not in st.session_state:
    st.session_state["bgm_volume"] = 0.1  # 初期音量（0.0〜1.0）
# ------------------------------------------------------

# ⭐ BGMはここで毎回セット（ページに関係なく）
autoplay_bgm("sounds/yurukawa_top_loop_v2.mp3", volume=st.session_state["bgm_volume"])


# ✅ 共通スタイル（フェードイン・XPアニメ・ボタン拡大）
st.markdown("""
<style>
/* 正解ボックスのフェードイン */
.correct-box {
    background-color: #E9FFE9;
    border-radius: 16px;
    border: 2px solid #88D788;
    padding: 18px 20px;
    color: #355E3B;
    font-size: 18px;
    margin: 10px 0 6px 0;
    animation: fadeInBox 0.4s ease-out;
}
.correct-box-title {
    font-weight: bold;
    font-size: 20px;
    margin-bottom: 6px;
}
.correct-box-monster {
    font-size: 28px;
    margin-right: 6px;
}

/* XPがふわっと出るアニメーション風 */
.xp-float {
    display: inline-block;
    margin-top: 4px;
    padding: 2px 10px;
    border-radius: 999px;
    background-color: #FFFBE6;
    border: 1px solid #FFD666;
    color: #996A00;
    font-weight: bold;
    animation: xpFloat 0.8s ease-out;
}

@keyframes fadeInBox {
    from { opacity: 0; transform: scale(0.96); }
    to   { opacity: 1; transform: scale(1.0); }
}

@keyframes xpFloat {
    from { opacity: 0; transform: translateY(8px); }
    50%  { opacity: 1; }
    to   { opacity: 0; transform: translateY(-8px); }
}

/* 次へ進む系のボタンを全体的に少し大きく＆押しやすく */
.stButton > button {
    font-size: 18px;
    padding: 0.6rem 1.4rem;
    border-radius: 999px;
}
</style>
""", unsafe_allow_html=True)

# ---------- セッション状態の初期化 ----------

# ページ（最初の1回だけ設定）
if "page" not in st.session_state:
    st.session_state["page"] = "home"

# XP：最初の1回だけファイルから読み込む
if "xp" not in st.session_state:
    st.session_state["xp"] = load_xp()
    
 # BGM音量（0.0〜1.0）
if "bgm_volume" not in st.session_state:
    st.session_state["bgm_volume"] = 0.1  # デフォルト50%

#  全ステージ共通：問題のクリア状態をまとめて管理
if "solved" not in st.session_state:
    # 例：{"1_0": True, "2_3": False} のように管理する
    st.session_state["solved"] = {}

# ----------------------------------------------------
# その他のセッション状態初期化
# ----------------------------------------------------
# 前回XP（称号判定用）
if "last_xp" not in st.session_state:
    st.session_state["last_xp"] = st.session_state["xp"]

# レベル状態
if "level" not in st.session_state:
    st.session_state["level"] = 1

# チャットメッセージ
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ログインボーナス関連
if "last_login_date" not in st.session_state:
    st.session_state["last_login_date"] = None

if "login_bonus_given_today" not in st.session_state:
    st.session_state["login_bonus_given_today"] = False

# --- プレイ日管理（フェーズ3用）---
if "last_play_date" not in st.session_state:
    st.session_state["last_play_date"] = None

if "show_return_banner" not in st.session_state:
    st.session_state["show_return_banner"] = False


# ステージ1用 ----------
if "stage1_index" not in st.session_state:
    st.session_state["stage1_index"] = 0
if "stage1_feedback" not in st.session_state:
    st.session_state["stage1_feedback"] = ""
if "stage1_step" not in st.session_state:
    # ⭐ -1 を導入画面として追加
    st.session_state["stage1_step"] = -1



# STEP0（写経）が正解だったかどうか
if "stage1_copy_correct" not in st.session_state:
    st.session_state["stage1_copy_correct"] = False
    
# ✅ 直近の3択が正解だったかどうか
if "stage1_last_answer_correct" not in st.session_state:
    st.session_state["stage1_last_answer_correct"] = False

# ✅ STEP2（もう一度書く）が正解だったかどうか
if "stage1_rewrite_correct" not in st.session_state:
    st.session_state["stage1_rewrite_correct"] = False


# ----------ステージ2用----------
if "stage2_index" not in st.session_state:
    st.session_state["stage2_index"] = 0

# ----------ステージ3用----------
if "stage3_index" not in st.session_state:
    st.session_state["stage3_index"] = 0

# 🔁 復習フラグ
if "stage1_review" not in st.session_state:
    st.session_state["stage1_review"] = False
if "stage2_review" not in st.session_state:
    st.session_state["stage2_review"] = False
if "stage3_review" not in st.session_state:
    st.session_state["stage3_review"] = False

# クリアフラグ
if "stage1_cleared" not in st.session_state:
    st.session_state["stage1_cleared"] = False
if "stage2_cleared" not in st.session_state:
    st.session_state["stage2_cleared"] = False
if "stage3_cleared" not in st.session_state:
    st.session_state["stage3_cleared"] = False


# ---------- レベル計算 ----------
def update_level():
    st.session_state["level"] = max(1, st.session_state["xp"] // 50 + 1)

# ---------- 正解表示のヘルパー関数 ----------
def show_correct_feedback(message: str, xp_gain: int, monster_emoji: str = "👾"):
    """
    正解したときの共通UI＋XP加算。
    XPが0のときはXPポップは表示しない。
    """

    html = f"""
    <div class="correct-box">
        <div class="correct-box-title">
            <span class="correct-box-monster">{monster_emoji}</span>
            正解だよ！
        </div>
        <div>{message}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    # ⭐ XPが0のときはポップを出さない
    if xp_gain > 0:
        st.markdown(f'<div class="xp-float">+{xp_gain} XP</div>', unsafe_allow_html=True)
        play_sound("sounds/stage_clear.mp3")

    # XP加算前の状態
    old_xp = st.session_state["xp"]
    old_title = get_title_by_xp(old_xp)["current_name"]

    # XP加算
    st.session_state["xp"] += xp_gain
    update_level()
    save_xp(st.session_state["xp"])

    # NEW称号チェック（xp_gain > 0 のときだけでOK）
    if xp_gain > 0:
        new_title = get_title_by_xp(st.session_state["xp"])["current_name"]
        if new_title != old_title:
            st.success(f"🌟 NEW称号 解放！ {new_title}")
            play_sound("sounds/new_title_unlock.mp3")

    st.session_state["last_xp"] = st.session_state["xp"]

# ---------- ログインボーナス ----------
today_str = datetime.date.today().isoformat()

# ===============================
# フェーズ3：3日以上あいた再開判定
# ===============================
today = datetime.date.today()

last_play_date = st.session_state.get("last_play_date")

if last_play_date:
    last = datetime.date.fromisoformat(last_play_date)
    if (today - last).days >= 3:
        st.session_state["show_return_banner"] = True
    else:
        st.session_state["show_return_banner"] = False
else:
    # 初回起動
    st.session_state["show_return_banner"] = False

# 最終プレイ日を更新（判定後に！）
st.session_state["last_play_date"] = today.isoformat()

# ---------- ログインボーナス判定 ----------
if st.session_state["last_login_date"] != today_str:
    st.session_state["last_login_date"] = today_str
    st.session_state["login_bonus_given_today"] = False



# ======================================================
#  ページ共通ヘッダー
# ======================================================
st.markdown(
    "<h1 style='text-align: center;'>🐣 ミナリアのPythonクエスト</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h4 style='text-align: center; color:#8E6E95;'>C O C O M O A   K I N G D O M</h4>",
    unsafe_allow_html=True,
)

# ======================================================
#  ページ: home
# ======================================================
if st.session_state["page"] == "home":
    autoplay_video("minaria.mp4")

    st.markdown(
        """
    <div style='text-align:center; padding:10px; font-size:18px; color:#5F4C5B;'>
    こんにちは、冒険者さん。<br>
    きょうも少しだけ、いっしょに歩いてみましょうね。🌼
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div style='text-align:center; font-size:16px; color:#6A5A78;'>
    ここはココモア王国。<br>
    学びが小さな魔法になる、ふんわり優しい世界なの。<br>
    Pythonの力で、バグモンスターたちを癒してあげましょう。  
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    


    # 1行目：導入 ＋ ステージ1
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        if st.button("🌱 冒険をはじめる"):
            st.session_state["page"] = "intro"
            st.rerun()
    with row1_col2:
        if st.button("🌱 ステージ1：ポヨンのはらっぱ"):
            st.session_state["page"] = "stage1"
            st.rerun()

    # 2行目：ステージ2 ＋ ステージ3
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        if st.button("🌿 ステージ2：もりねむの小道"):
            st.session_state["page"] = "stage2"
            st.rerun()
    with row2_col2:
        if st.button("🌀 ステージ3：くるくるループの塔"):
            st.session_state["page"] = "stage3"
            st.rerun()

    st.markdown("---")
    

    # マイページボタン
    if st.button("📊 マイページ"):
        st.session_state["page"] = "mypage"
        st.rerun()

    st.markdown(
        "<div style='text-align:center; color:#A195A6; margin-top:20px;'>ココモア王国より 🌼</div>",
        unsafe_allow_html=True,
    )

# ======================================================
#  ページ: 導入シナリオ
# ======================================================
elif st.session_state["page"] == "intro":

        # ミナリア画像
        st.image("minaria.png", use_container_width=True)

        # ★ 成長フェーズに応じた「約束」バナー（画像の直下）
        render_promise_banner()

        st.markdown("---")

        # イントロテキスト
        st.markdown(
            """
            ### ようこそ、ココモア王国へ 🌱

            ここは、Pythonの魔法で  
            こまっているモンスターを助けながら、  
            **パソコンへのお願いのしかた**を学ぶ場所です。

            むずかしい言葉は、できるだけ使いません。  
            まちがえても大丈夫。  
            ミナリアと一緒に、ゆっくり進みましょう。
            """
        )

        # ボタン類（既存のものをそのまま）
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🌟 冒険をはじめる"):
                st.session_state["page"] = "home"
                st.rerun()

        with col2:
            if st.button("📖 つかいかたを見る"):
                st.session_state["page"] = "help"
                st.rerun()



# ======================================================
#  ページ: ステージ1 ポヨンのはらっぱ（写経＋3択＋写経）
# ======================================================
elif st.session_state["page"] == "stage1":

    st.subheader("🌱 ステージ1：ポヨンのはらっぱ")

    idx = st.session_state["stage1_index"]
    step = st.session_state["stage1_step"]

    # ---------------------------------------------------
    # q（問題データ）は最初に必ず定義しておく
    # ---------------------------------------------------
    if idx < len(STAGE1_QUESTIONS):
        q = STAGE1_QUESTIONS[idx]
    else:
        q = None  # 全問クリア時のみ None

    # ---------------------------------------------------
    # ⭐ STEP -1：導入画面（説明 → はじめるボタン）
    # ---------------------------------------------------
    if step == -1:

        st.markdown(
            """
        ここは、ココモア王国の入口「ポヨンのはらっぱ」。  
        地面がぽよんぽよんしていて、はじめての冒険者でも安心して歩ける場所です。  

        ここでは **print** と **変数** の、いちばんやさしい魔法を練習するよ。  
        1つの魔法ごとに「まねして書く → えらぶ → もう一度書く」という流れで進みます。
        """
        )

        st.markdown("---")

        # 📌 ミナリアの一言（printの不安を消す）
        st.markdown("""
        <div style="
          background:#FFF4D6;
          padding:16px 18px;
          border-radius:14px;
          border-left:6px solid #E6A800;
          color:#1F2A37;
          font-size:16px;
          line-height:1.8;
        ">
          <b style="font-size:17px;">📌 ミナリアからのひとこと</b><br><br>
          print はね、<br>
          <span style="font-weight:700; color:#0F172A;">
            「作業の途中経過を画面に出すメモ」
          </span>
          みたいなものよ。<br>
          これができると、エラーで迷子になりにくくなるの。
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        ### 🗺 このステージで手に入るスキル
        - ① print：画面に表示して“今なにが起きてるか”を確認できる
        - ② 変数：値を箱に入れて、あとで使い回せる
        - ③ 計算＋print：計算結果を表示できる（ミスが減る）
        """)

        play_sound("sounds/minaria_Poyon.mp3")
        

        if st.button("🌱 はじめる"):
            st.session_state["stage1_step"] = 0
            st.rerun()

        st.stop()

    # ---------------------------------------------------
    # STEP -1 を越えたので通常ステージ画面へ
    # ---------------------------------------------------

    # 進捗バー
    total1 = len(STAGE1_QUESTIONS)
    render_question_progress(idx, total1, label="ステージ1の進み具合：")

    # ---------------------------------------------------
    # 🌟 全問クリア
    # ---------------------------------------------------
    if q is None:  # idx が範囲外
        st.session_state["stage1_cleared"] = True

        st.success("✨ ステージ1『ポヨンのはらっぱ』をクリアしたよ！")
        st.info("ミナリア：最初の一歩を踏み出せたね。本当にえらいわ。次のステージも、あなたのペースでいきましょうね。")

        autoplay_video("stage1_clear.mp4", width="70%")

        if st.button("🔁 このステージを最初から復習する"):
            st.session_state["stage1_index"] = 0
            st.session_state["stage1_step"] = -1
            st.session_state["stage1_review"] = True
            st.rerun()

        st.stop()

    # ---------------------------------------------------
    # 👾 モンスター表示（STEP 0〜2 共通）
    # ---------------------------------------------------
    st.markdown("---")
    st.markdown(f"### 👾 きょうのバグモンスター：{q['monster_name']}")

    monster = q["monster_name"]

    if "prev_monster" not in st.session_state or st.session_state["prev_monster"] != monster:
        voice_path = q.get("voice_file")
        if voice_path:
            play_sound(voice_path)

    st.session_state["prev_monster"] = monster

    img_path = q.get("monster_image")
    if img_path and os.path.exists(img_path):
        st.image(img_path, use_container_width=True)
    else:
        st.caption("※ まだイラストは準備中だよ")

    st.markdown(q["monster_desc"])
    st.markdown("---")

    # ======================================================
    # STEP 0：見本どおりに写す
    # ======================================================
    if step == 0:

        st.info(q["lesson_intro"])

        st.markdown("#### ✏ まずは見本どおりに書いてみよう")
        st.code(q["copy_sample"], language="python")

        code_input = st.text_area(
            "ここにまねして書いてみてね：",
            key=f"stage1_copy_{idx}",
            height=80,
        )
        
        #st.code("Hello, world!", language=None)
        
        # --------------------------------------
        # 👀 実行するとこう表示されるよ（出力）
        # ※ 正解の print から自動生成
        # --------------------------------------

        sample_code = q["copy_sample"].replace("'", '"')

        st.markdown("#### 👀 実行するとこうなるよ（見本）")

        # ① print("文字列")
        m_print_str = re.search(r'print\s*\(\s*"(.+?)"\s*\)', sample_code)
        if m_print_str:
            st.code(m_print_str.group(1), language=None)
            st.caption("print() は文字をそのまま表示する魔法だよ。")

        else:
            # ② print(数字 + 数字)
            m_calc = re.search(r'print\s*\(\s*([0-9+\-*/\s]+)\s*\)', sample_code)
            if m_calc:
                try:
                    result = eval(m_calc.group(1))
                    st.code(str(result), language=None)
                    st.caption("中の計算をしてから、結果を表示しているよ。")
                except Exception:
                    st.code("（計算結果）", language=None)

            else:
                # ③ その他（代入など）
                st.code("（画面には何も表示されません）", language=None)
                st.caption("この問題は、準備や仕組みを学ぶステップだよ。")



        # --------------------------------------
        # ✅ 正解チェック（1回だけ押せる）
        # --------------------------------------
        if one_time_button(
            "できたかチェック",
            key=f"stage1_copy_btn_{idx}",
            allow_retry=st.session_state.get("stage1_review", False),
        ):

            if not code_input.strip():
                st.warning("なにも入力されていないみたい。少しだけでいいから、まねして書いてみよう。")
                st.session_state["stage1_copy_correct"] = False

            elif normalize_code(code_input) == normalize_code(q["copy_sample"]):

                st.session_state["stage1_copy_correct"] = True
                st.session_state[f"stage1_last_copy_code_{idx}"] = code_input

                # ⭐ フィードバック（XP）
                if st.session_state.get("stage1_review", False):
                    show_correct_feedback(
                        message="ばっちり！見本どおりに書けたよ。（復習モードなのでXPは変わらないよ）",
                        xp_gain=0,
                        monster_emoji="🐣",
                    )
                else:
                    award_xp_once(
                        key=f"stage1_{idx}_step0",
                        xp=10,
                        message="ばっちり！見本どおりに書けたよ。下で実行して結果を見てみよう。",
                        emoji="🐣",
                    )

            else:
                st.error("うーん、少しちがうみたい。スペルやカッコの位置を見比べてみよう。")
                st.session_state["stage1_copy_correct"] = False

        # ==================================================
        # 🎯 正解後：printの「現象」を体験させるゾーン
        # ==================================================
        if st.session_state.get("stage1_copy_correct", False):

            if st.button("▶ 実行してみる", key=f"run_stage1_copy_{idx}"):

                

                code = st.session_state.get(f"stage1_last_copy_code_{idx}", "")
                code = code.replace("'", '"')

                # -----------------------------
                # ① print("文字列") の場合
                # -----------------------------
                m_print_str = re.search(r'print\s*\(\s*"(.+?)"\s*\)', code)
                if m_print_str:
                    st.markdown("#### 📺 出力")
                    st.code(m_print_str.group(1), language=None)
                    st.success("💡 print の中に書いた文字が、そのまま表示されているよ！")

                else:
                    # -----------------------------
                    # ② 変数代入 → print(name) の場合
                    # -----------------------------
                    m_assign = re.search(
                        r'^\s*([a-zA-Z_]\w*)\s*=\s*"(.+?)"\s*$',
                        code,
                        flags=re.M
                    )

                    m_print_var = re.search(
                        r'print\s*\(\s*([a-zA-Z_]\w*)\s*\)',
                        code
                    )

                    if m_assign and m_print_var:
                        var_name, var_value = m_assign.group(1), m_assign.group(2)
                        printed_var = m_print_var.group(1)

                        if var_name == printed_var:
                            st.markdown("#### 📺 出力")
                            st.code(var_value, language=None)
                            st.success(
                                f'💡 {var_name} に入れた "{var_value}" が表示されているよ！'
                            )
                        else:
                            st.info("変数に入れた名前と、printで表示した名前がちがうみたい。")

                    # -----------------------------
                    # ③ 代入だけ（表示はされない）
                    # -----------------------------
                    elif m_assign:
                        var_name, var_value = m_assign.group(1), m_assign.group(2)
                        st.markdown("#### 📺 出力")
                        st.code("（画面には何も表示されません）", language=None)
                        st.info(
                            f'これは「{var_name} に "{var_value}" を入れる練習」だよ。'
                            " 表示されないのが正解！"
                        )

                    else:
                        st.info("この問題は、表示のしくみを練習するステップだよ。")



            if st.button("▶ クイズに進む", key=f"stage1_to_quiz_{idx}"):
                st.session_state["stage1_step"] = 1
                st.session_state["stage1_copy_correct"] = False
                st.rerun()


    # ======================================================
    # STEP 1：3択問題
    # ======================================================
    elif step == 1:

        st.markdown(f"**{q['text']}**")

        last_code = st.session_state.get(f"stage1_last_copy_code_{idx}")
        if last_code:
            with st.expander("💾 さっき写したコードをもう一度見る"):
                st.code(last_code, language="python")

        choice_key = f"stage1_choice_{idx}"
        user_choice = st.radio(
            "正しいと思うものをえらんでね：",
            q["choices"],
            index=None,
            key=choice_key,
        )

        if st.button("解答する", key=f"stage1_submit_{idx}"):

            if user_choice is None:
                st.warning("どれか1つを選んでから、『解答する』を押してね。")
                st.session_state["stage1_last_answer_correct"] = False

            else:
                correct_choice = q["choices"][q["correct_index"]]

                if user_choice == correct_choice:

                    if st.session_state.get("stage1_review", False):
                        st.success("⭕ 正解！（復習モードなのでXPは変わらないよ）")
                        st.info(f"ミナリア：{q['explain']}")
                    else:
                        award_xp_once(
                            key=f"stage1_{idx}_step1",
                            xp=20,
                            message="バグモンスターがにこっと笑ったよ！",
                            emoji="🟢",
                        )
                        
                        st.info(f"ミナリア：{q['explain']}")

                    st.session_state["stage1_last_answer_correct"] = True

                else:
                    st.error("❌ ざんねん…！でも大丈夫、ここで迷うのはふつうだよ。")
                    st.info(f"ミナリア：ヒントね。{q['hint']}")
                    st.session_state["stage1_last_answer_correct"] = False

        if st.session_state.get("stage1_last_answer_correct", False):
            if st.button("▶ 次へ進む", key=f"stage1_next_{idx}"):
                st.session_state["stage1_step"] = 2
                st.session_state["stage1_last_answer_correct"] = False
                st.rerun()

    # ======================================================
    # STEP 2：もう一度書く
    # ======================================================
    elif step == 2:

        st.markdown("#### ✏ もう一度、自分の手で書いてみよう")
        st.markdown(q["rewrite_prompt"])

        last_code = st.session_state.get(f"stage1_last_copy_code_{idx}")
        if last_code:
            with st.expander("💾 さっき写したコードを見る"):
                st.code(last_code, language="python")

        rewrite_input = st.text_area(
            "ここにコードを書いてみてね：",
            key=f"stage1_rewrite_{idx}",
            height=80,
        )

        # 🔘 判定ボタン
        if st.button("できたかチェック", key=f"stage1_rewrite_btn_{idx}"):

            # 入力なしチェック
            if not rewrite_input.strip():
                st.warning("まだ何も書かれていないみたい。1行だけでいいよ。")
                st.session_state["stage1_rewrite_correct"] = False

            else:
                is_correct = False

                # ②問目（変数 name の問題）だけ、「好きな名前OK」にする
                if idx == 1:
                    if is_valid_name_assignment(rewrite_input):
                        is_correct = True
                else:
                    # 通常の判定：模範解答と一致
                    if normalize_code(rewrite_input) == normalize_code(q["rewrite_answer"]):
                        is_correct = True

                # 🎉 正解 / 不正解処理
                if is_correct:
                    if st.session_state.get("stage1_review", False):
                        st.success("✨ いい感じ！（復習モードなのでXPなし）")
                    else:
                        award_xp_once(
                            key=f"stage1_{idx}_step2",
                            xp=20,
                            message="自分の力で書けたね！とってもいい感じ！",
                            emoji="✨",
                            )
                        
                    st.session_state["stage1_rewrite_correct"] = True

                else:
                    st.error("うーん、少し違うみたい。見本の形を思い出してみよう。")
                    st.session_state["stage1_rewrite_correct"] = False

        # ▶ 次へボタン
        if st.session_state.get("stage1_rewrite_correct", False):
            if st.button("▶ 次の問題へ", key=f"stage1_next_question_{idx}"):
                st.session_state["stage1_index"] += 1
                st.session_state["stage1_step"] = 0
                st.session_state["stage1_rewrite_correct"] = False
                st.rerun()

    # ---------------------------------------------------
    # ページ下部の共通ボタン（どのSTEPでも表示）
    # ---------------------------------------------------
    st.markdown("---")

    if st.button("👩‍🍼 ミナリアとお話する（チャットへ）"):
        st.session_state["page"] = "chat"
        st.rerun()

    if st.button("🏠 タイトルにもどる"):
        st.session_state["page"] = "home"
        st.rerun()


# ======================================================
#  ページ: ステージ2 もりねむの小道（if文 3択＋モンスター）
# ======================================================
elif st.session_state["page"] == "stage2":
    st.subheader("🌿 ステージ2：もりねむの小道")

    st.markdown(
        """
    ここは、少しだけ奥に進んだ「もりねむの小道」。  
    木々がゆらゆら揺れていて、「行こうかな、どうしようかな」と迷っているように見える場所です。  

    ここでは **if文** の魔法を練習します。  
    条件によって、やることを変えられる「分かれ道の魔法」だよ。  
    3つの選択肢から、正しそうなものを選んでね。
    """
    )

    idx2 = st.session_state["stage2_index"]
    
    # ステージ進捗バー
    total2 = len(STAGE2_QUESTIONS)
    render_question_progress(idx2, total2, label="ステージ2の進み具合：")

    if idx2 >= len(STAGE2_QUESTIONS):
        st.session_state["stage2_cleared"] = True

        st.success("✨ ステージ2『もりねむの小道』をクリアしたよ！")
        st.info("ミナリア：条件で動きを変える魔法、だいぶわかってきたみたいね。とっても素敵よ。")
        
        # 🎞 ステージ2クリアアニメーション
        autoplay_video("stage2_clear.mp4", width="70%")

        if st.button("🔁 このステージを最初から復習する"):
            st.session_state["stage2_index"] = 0
            st.session_state["stage2_review"] = True
            st.rerun()

    else:
        q2 = STAGE2_QUESTIONS[idx2]

        st.markdown("---")
        st.markdown(f"### 👾 きょうのバグモンスター：{q2['monster_name']}")

        img_path2 = q2.get("monster_image")
        if img_path2 and os.path.exists(img_path2):
            st.image(img_path2, use_container_width=True)
        else:
            st.caption("※ まだイラストは準備中だけど、ここにモンスターの絵が入る予定だよ。")

        st.markdown(q2["monster_desc"])
        st.markdown("---")

        st.markdown(f"**{q2['text']}**")

        choice_key2 = f"stage2_choice_{idx2}"
        user_choice2 = st.radio(
            "正しいと思うものをえらんでね：",
            q2["choices"],
            index=None,
            key=choice_key2,
        )

        # ⭐ 解答ボタンと判定ロジックは「else」の中にネストする
        if st.button("解答する", key=f"stage2_submit_{idx2}"):

            # 選択されていない場合
            if user_choice2 is None:
                st.warning("どれか1つを選んでから、『解答する』ボタンを押してね。")

            else:
                correct_choice2 = q2["choices"][q2["correct_index"]]

                # 正解した場合
                if user_choice2 == correct_choice2:

                    # ⭐ 復習モード → XPは与えない
                    if st.session_state.get("stage2_review", False):
                        st.success("⭕ 正解！森のバグモンスターがほっとした顔で帰っていったよ。（復習モードなのでXPは変わらないよ）")
                        st.info(f"ミナリア：{q2['explain']}")

                    # ⭐ 初回 or 2回目以降 → award_xp_once が自動判定
                    else:
                        award_xp_once(
                            key=f"stage2_{idx2}",
                            xp=25,
                            message="⭕ 正解！バグモンスターが、ほっとした顔で森の奥へ帰っていったよ。",
                            emoji="🌳",
                        )
                        st.info(f"ミナリア：{q2['explain']}")

                    # 次の問題へ進む
                    st.session_state["stage2_index"] += 1
                    st.rerun()

                # ❌ 不正解の場合
                else:
                    st.error("❌ ざんねん…！でも大丈夫、ここで迷うのは当たり前なの。")
                    st.info(f"ミナリア：ヒントね。{q2['hint']}")

        st.markdown("---")
        if st.button("👩‍🍼 ミナリアとお話する（チャットへ）"):
            st.session_state["page"] = "chat"
            st.rerun()

        if st.button("🏠 タイトルにもどる"):
            st.session_state["page"] = "home"
            st.rerun()


# ======================================================
#  ページ: ステージ3 くるくるループの塔（for文 3択＋モンスター）
# ======================================================
elif st.session_state["page"] == "stage3":
    st.subheader("🌀 ステージ3：くるくるループの塔")

    st.markdown(
        """
    ここは、同じ階段をぐるぐる回ってしまう「くるくるループの塔」。  
    まよっているバグモンスターたちに、**for文** の魔法で「何回くり返すか」を教えてあげよう。  

    3つの選択肢から、正しそうなコードを選んでね。
    """
    )

    idx3 = st.session_state["stage3_index"]

    # ステージ進捗バー
    total3 = len(STAGE3_QUESTIONS)
    render_question_progress(idx3, total3, label="ステージ3の進み具合：")

    # クリア判定
    if idx3 >= len(STAGE3_QUESTIONS):
        st.session_state["stage3_cleared"] = True

        st.success("✨ ステージ3『くるくるループの塔』をクリアしたよ！")
        st.info("ミナリア：くり返しの魔法まで身についたなんて、本当にすごいわ。これで基礎の魔法はばっちりね。")

        autoplay_video("stage3_clear.mp4", width="70%")

        if st.button("🔁 このステージを最初から復習する"):
            st.session_state["stage3_index"] = 0
            st.session_state["stage3_review"] = True
            st.rerun()

    else:
        q3 = STAGE3_QUESTIONS[idx3]

        st.markdown("---")
        st.markdown(f"### 👾 きょうのバグモンスター：{q3['monster_name']}")

        img_path3 = q3.get("monster_image")
        
        if img_path3 and os.path.exists(img_path3):
            st.image(img_path3, use_container_width=True)
        else:
            st.caption("※ まだイラストは準備中だけど、ここにモンスターの絵が入る予定だよ。")

        st.markdown(q3["monster_desc"])
        st.markdown("---")

        st.markdown(f"**{q3['text']}**")

        choice_key3 = f"stage3_choice_{idx3}"
        user_choice3 = st.radio(
            "正しいと思うものをえらんでね：",
            q3["choices"],
            index=None,
            key=choice_key3,
        )

        if st.button("解答する", key=f"stage3_submit_{idx3}"):

            # まだ何も選んでないとき
            if user_choice3 is None:
                st.warning("どれか1つを選んでから、『解答する』ボタンを押してね。")

            else:
                correct_choice3 = q3["choices"][q3["correct_index"]]

                if user_choice3 == correct_choice3:

                    if st.session_state.get("stage3_review", False):
                        st.success("⭕ 正解！塔の階段をスイスイのぼっていけるようになったよ。（復習モードなのでXPは変わらないよ）")
                        st.info(f"ミナリア：{q3['explain']}")

                    else:
                        award_xp_once(
                            key=f"stage3_{idx3}",
                            xp=30,
                            message="⭕ 正解！高い塔の階段も、スイスイのぼれるようになってきたよ！",
                            emoji="🗼",
                        )
                        st.info(f"ミナリア：{q3['explain']}")

                    st.session_state["stage3_index"] += 1
                    st.rerun()

                else:
                    st.error("❌ ざんねん…！でも大丈夫、くり返しは少しずつ慣れていけばいいのよ。")
                    st.info(f"ミナリア：ヒントね。{q3['hint']}")


        st.markdown("---")
        if st.button("👩‍🍼 ミナリアとお話する（チャットへ）"):
            st.session_state["page"] = "chat"
            st.rerun()

        if st.button("🏠 タイトルにもどる"):
            st.session_state["page"] = "home"
            st.rerun()



# ======================================================
#  ページ: チャット
# ======================================================
elif st.session_state["page"] == "chat":
    with st.sidebar:
        st.header("📊 ステータス")
        st.write(f"レベル：**{st.session_state['level']}**")
        st.write(f"経験値（XP）：**{st.session_state['xp']}**")

        if not st.session_state["login_bonus_given_today"]:
            st.info("🎁 きょうのログインボーナスがあるよ。「ログインボーナスちょうだい」と話しかけてみてね。")

        if st.button("🌱 ステージ1で練習する"):
            st.session_state["page"] = "stage1"
            st.rerun()

    st.subheader("💬 ミナリアとの会話")

    user_input = st.text_input("ミナリアに話しかけてみよう：", "")

    if st.button("送信") and user_input.strip():
        try:
            response = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": MINARIA_SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                ],
            )
            reply = response.output_text

            st.session_state["messages"].append(("あなた", user_input))
            st.session_state["messages"].append(("ミナリア", reply))

            gained_xp = 10

            if (("ログインボーナス" in user_input) or ("ボーナス" in user_input)) and not st.session_state[
                "login_bonus_given_today"
            ]:
                bonus_item = random.choice(
                    [
                        ("ミニポーション", 5),
                        ("ラッキーキャンディ", 10),
                        ("ふわふわ毛玉", 8),
                    ]
                )
                item_name, item_xp = bonus_item
                gained_xp += item_xp
                st.session_state["login_bonus_given_today"] = True
                st.success(f"🎁 ミナリアから『{item_name}』をもらった！ 追加で {item_xp} XP ゲット！")

            st.session_state["xp"] += gained_xp
            save_xp(st.session_state["xp"])
            update_level()

        except Exception as e:
            reply = f"エラーが起きちゃったみたい…ごめんね💦 詳細：{e}"
            st.session_state["messages"].append(("あなた", user_input))
            st.session_state["messages"].append(("ミナリア", reply))

    st.markdown("---")
    st.subheader("📜 会話ログ")
    if not st.session_state["messages"]:
        st.write("まだミナリアとの会話ははじまっていません。なにか話しかけてみてね 🌼")
    else:
        for speaker, text in st.session_state["messages"]:
            if speaker == "あなた":
                st.markdown(f"**🧑 あなた：** {text}")
            else:
                st.markdown(f"**👩‍🍼 ミナリア：** {text}")

    if st.button("🏠 タイトルにもどる"):
        st.session_state["page"] = "home"
        st.rerun()
        
    


# ======================================================
#  ページ: マイページ（進捗ダッシュボード）
# ======================================================
elif st.session_state["page"] == "mypage":

    st.subheader("📊 冒険者マイページ")
        
    st.markdown("### 🧑‍🚀 ステータス")
    # play_sound("sounds/yurukawa_top_loop_v2.mp3")
    
    # -------------------------
    # XP 称号システム（表示）
    # -------------------------
    xp = st.session_state.get("xp", 0)
    title_info = get_title_by_xp(xp)

    # 現在の称号バッジ
    st.markdown(
        f"""
        <div style="
            padding:12px;
            border-radius:12px;
            border:1px solid #DDC7F7;
            background-color:#F9F5FF;
            margin-top:10px;
            margin-bottom:10px;
        ">
            <div style="font-size:18px; color:#5F4C5B; font-weight:bold;">
                🏅 あなたの今の称号：{title_info["current_name"]}
            </div>
            <div style="font-size:14px; color:#7A6A80; margin-top:4px;">
                総XP：<b>{xp}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 次の称号がある場合のみ
    if title_info["next_name"]:
        st.markdown(
            f"次の称号 <b>{title_info['next_name']}</b> まで、あと <b>{title_info['need_xp']}</b> XP",
            unsafe_allow_html=True,
        )
        st.progress(title_info["progress_ratio"])
    else:
        st.success("🎉 あなたは最高ランク「ココモア王国のまもりびと」に到達しました！")


    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**レベル：{st.session_state['level']}**")
    with col_b:
        st.markdown(f"**経験値（XP）：{st.session_state['xp']}**")

    st.markdown("---")

    # -------------------------
    # ステージ進捗（solved ベース）
    # -------------------------
    solved = st.session_state.get("solved", {})

    # 🌱 ステージ1：各問題の「STEP2 まで解き切った数」をカウント
    total_stage1 = len(STAGE1_QUESTIONS)
    done_stage1 = sum(
        1 for i in range(total_stage1)
        if solved.get(f"stage1_{i}_step2", False)
    )

    # 🌿 ステージ2：各問題ごとに1回正解したか
    total_stage2 = len(STAGE2_QUESTIONS)
    done_stage2 = sum(
        1 for i in range(total_stage2)
        if solved.get(f"stage2_{i}", False)
    )

    # 🌀 ステージ3：各問題ごとに1回正解したか
    total_stage3 = len(STAGE3_QUESTIONS)
    done_stage3 = sum(
        1 for i in range(total_stage3)
        if solved.get(f"stage3_{i}", False)
    )



    def stage_badge(done, total):
        if done >= total:
            return "💚 <b>CLEAR!</b>", "#B7EB8F"
        elif done == 0:
            return "⬜ <b>未スタート</b>", "#C9B4F9"
        else:
            return "🟡 <b>進行中…</b>", "#FFF6DA"


# ======================================================
#  ステージ進捗
# ======================================================
    def stage_card(title, done, total):
        badge_text, bg_color = stage_badge(done, total)
        ratio = min(done / total, 1.0)

        st.markdown(
            f"""
            <div style="
                background-color:{bg_color};
                padding:15px;
                border-radius:15px;
                border:1px solid #DDD;
                margin-bottom:12px;
            ">
                <div style="font-size:20px; font-weight:bold; color:#5F4C5B;">{title}</div>
                <div style="margin:5px 0; font-size:16px; color:#5F4C5B;">
                    進捗：<b>{done} / {total}</b> 問　
                    {badge_text}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.progress(ratio)

    st.markdown("### 🗺 ステージ進捗")

    stage_card("🌱 ステージ1：ポヨンのはらっぱ", done_stage1, total_stage1)
    stage_card("🌿 ステージ2：もりねむの小道", done_stage2, total_stage2)
    stage_card("🌀 ステージ3：くるくるループの塔", done_stage3, total_stage3)

    st.markdown("---")

    st.markdown("### 🎖 次のおすすめ行動")
    if done_stage1 < total_stage1:
        st.write("🌱 まずは **ステージ1** を終わらせてみよう。print と 変数の魔法を完成させようね。")
    elif done_stage2 < total_stage2:
        st.write("🌿 次は **ステージ2** だよ。条件分岐の if 文をいっしょに練習しよう。")
    elif done_stage3 < total_stage3:
        st.write("🌀 ここまで来たら **ステージ3** にチャレンジ！for 文のくり返しが使えると、一気にできることが増えるよ。")
    else:
        st.success("✨ すごい！今あるステージはぜんぶ CLEAR しているよ！Python基礎の魔法はばっちり。")

    st.markdown("---")

    col_back1, col_back2 = st.columns(2)
    with col_back1:
        if st.button("🏠 タイトルにもどる"):
            st.session_state["page"] = "home"
            st.rerun()
    with col_back2:
        if st.button("👩‍🍼 ミナリアとお話する（チャットへ）"):
            st.session_state["page"] = "chat"
            st.rerun()
