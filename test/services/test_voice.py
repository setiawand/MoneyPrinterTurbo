import asyncio
import base64
import os
import shutil
import subprocess
import unittest
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils import utils
from app.services import voice as vs
from app.services import task as task_service
from pydub import AudioSegment

temp_dir = utils.storage_dir("temp")

text_en = """
What is the meaning of life? 
This question has puzzled philosophers, scientists, and thinkers of all kinds for centuries. 
Throughout history, various cultures and individuals have come up with their interpretations and beliefs around the purpose of life. 
Some say it's to seek happiness and self-fulfillment, while others believe it's about contributing to the welfare of others and making a positive impact in the world. 
Despite the myriad of perspectives, one thing remains clear: the meaning of life is a deeply personal concept that varies from one person to another. 
It's an existential inquiry that encourages us to reflect on our values, desires, and the essence of our existence.
"""

text_zh = """
预计未来3天深圳冷空气活动频繁，未来两天持续阴天有小雨，出门带好雨具；
10-11日持续阴天有小雨，日温差小，气温在13-17℃之间，体感阴凉；
12日天气短暂好转，早晚清凉；
"""

voice_rate=1.0
voice_volume=1.0
RUN_INTEGRATION_TESTS = os.environ.get("MPT_RUN_INTEGRATION_TESTS", "").lower() in {
    "1",
    "true",
    "yes",
}
                    
class TestVoiceService(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()





    def test_no_voice_tts_generates_silent_audio_and_subtitle_timeline(self):
        """
        无配音模式不调用任何外部 TTS provider，只生成静音音频作为时间轴占位。
        这里 mock FFmpeg，验证请求参数、输出文件和 legacy 字幕结构都符合后续
        视频合成链路的预期。
        """

        def fake_run(command, capture_output, text, check, **kwargs):
            self.assertEqual(command[0], "/tmp/fake-ffmpeg")
            self.assertIn("anullsrc=r=44100:cl=mono", command)
            Path(command[-1]).write_bytes(b"fake-silent-mp3")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            vs.utils,
            "get_ffmpeg_binary",
            return_value="/tmp/fake-ffmpeg",
        ), patch.object(vs.subprocess, "run", side_effect=fake_run):
            voice_file = str(Path(tmp_dir) / "silent.mp3")
            sub_maker = vs.tts(
                text="第一句话。Second sentence.",
                voice_name=vs.NO_VOICE_NAME,
                voice_rate=1.0,
                voice_file=voice_file,
            )

            self.assertEqual(Path(voice_file).read_bytes(), b"fake-silent-mp3")

        self.assertIsNotNone(sub_maker)
        self.assertEqual(getattr(sub_maker, "subs", []), ["第一句话", "Second sentence"])
        self.assertEqual(len(getattr(sub_maker, "offset", [])), 2)
        self.assertGreater(vs.get_audio_duration(sub_maker), 0)

    def test_get_audio_duration_accepts_non_mp3_files(self):
        """
        自定义音频（custom_audio_file）常见为 m4a/wav/aac 等非 mp3 格式。
        get_audio_duration 不应因扩展名不是 .mp3 就报 "Invalid target type" 并返回 0，
        而应交给 moviepy(ffmpeg) 读取真实时长。
        """
        for path in ("custom-audio.m4a", "voice.wav", "clip.aac"):
            with patch.object(vs.os.path, "exists", return_value=True), \
                    patch.object(vs, "AudioFileClip") as mock_afc:
                mock_afc.return_value.__enter__.return_value.duration = 28.89
                self.assertEqual(vs.get_audio_duration(path), 28.89)
                mock_afc.assert_called_once_with(path)

    def test_get_audio_duration_missing_file_returns_zero(self):
        """音频文件不存在时安全返回 0，而不是抛异常或读取失败。"""
        with patch.object(vs.os.path, "exists", return_value=False):
            self.assertEqual(vs.get_audio_duration("does-not-exist.m4a"), 0.0)

    def test_no_voice_alias_none_is_supported_temporarily(self):
        """
        兼容 PR #981 曾使用过的 none sentinel，避免少量直接调用 API 的用户
        升级后立即失效。新 UI 和新代码仍统一使用 no-voice。
        """
        self.assertTrue(vs.is_no_voice("none"))
        self.assertTrue(vs.is_no_voice(vs.NO_VOICE_NAME))
        self.assertFalse(vs.is_no_voice(""))

    def test_no_voice_duration_estimates_non_ascii_languages(self):
        """
        无配音没有真实 TTS 音频，只能根据脚本文字估算阅读时间。俄语、阿拉伯语、
        日文假名、韩文等非 ASCII 文本也必须参与估算，不能都落到最短 3 秒。
        """
        russian_text = (
            "Это длинный тестовый сценарий без озвучки. "
            "Он должен получить достаточно времени для чтения субтитров."
        )
        arabic_text = "هذا اختبار طويل بدون تعليق صوتي، ويجب أن يحصل على وقت كاف لقراءة الترجمة."

        self.assertGreater(vs.estimate_no_voice_duration(russian_text), 8.0)
        self.assertGreater(vs.estimate_no_voice_duration(arabic_text), 8.0)

    def test_generate_silent_audio_rejects_missing_output_file(self):
        """
        即使 FFmpeg 进程返回成功，也要确认输出文件真实存在且非空。这样可以把
        异常收敛在 TTS 阶段，而不是拖到后续视频合成阶段才暴露。
        """
        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            vs.utils,
            "get_ffmpeg_binary",
            return_value="/tmp/fake-ffmpeg",
        ), patch.object(
            vs.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
        ):
            voice_file = str(Path(tmp_dir) / "missing-silent.mp3")

            self.assertFalse(vs.generate_silent_audio(3.0, voice_file))

    def test_no_voice_ffmpeg_timeout_preserves_previous_output(self):
        def timed_out(command, **kwargs):
            self.assertIn("-nostdin", command)
            self.assertGreater(kwargs.get("timeout", 0), 0)
            Path(command[-1]).write_bytes(b"partial-silence")
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "silent.mp3"
            output.write_bytes(b"previous-success")
            with patch.object(vs.subprocess, "run", side_effect=timed_out):
                self.assertFalse(vs.generate_silent_audio(3.0, str(output)))
            self.assertEqual(output.read_bytes(), b"previous-success")

    def test_empty_voice_name_does_not_enable_no_voice_mode(self):
        """
        空 voice 通常意味着配置缺失或接口参数错误，不能自动切到无配音模式。
        否则用户填错 TTS 配置时也会得到一个“成功”的静音视频，定位成本更高。
        """
        result = vs.tts(
            text="empty voice must not become a silent video",
            voice_name="",
            voice_rate=1.0,
            voice_file="/tmp/empty-voice.mp3",
        )

        self.assertIsNone(result)

    @unittest.skipUnless(
        RUN_INTEGRATION_TESTS,
        "MPT_RUN_INTEGRATION_TESTS not set",
    )
    def test_siliconflow(self):
        # SiliconFlow 的 API Key 存在 [siliconflow].api_key 中，运行时代码也是从
        # config.siliconflow 读取；这里必须使用同一配置源，避免正确配置凭据时
        # 测试仍然被误跳过。
        if not vs.config.siliconflow.get("api_key"):
            self.skipTest("siliconflow_api_key is not configured")

        voice_name = "siliconflow:FunAudioLLM/CosyVoice2-0.5B:alex-Male"
        voice_name = vs.parse_voice_name(voice_name)
        
        async def _do():
            parts = voice_name.split(":")
            if len(parts) >= 3:
                model = parts[1]
                # 移除性别后缀，例如 "alex-Male" -> "alex"
                voice_with_gender = parts[2]
                voice = voice_with_gender.split("-")[0]
                # 构建完整的voice参数，格式为 "model:voice"
                full_voice = f"{model}:{voice}"
                voice_file = f"{temp_dir}/tts-siliconflow-{voice}.mp3"
                subtitle_file = f"{temp_dir}/tts-siliconflow-{voice}.srt"
                sub_maker = vs.siliconflow_tts(
                    text=text_zh, model=model, voice=full_voice, voice_file=voice_file, voice_rate=voice_rate, voice_volume=voice_volume
                )
                if not sub_maker:
                    self.fail("siliconflow tts failed")
                vs.create_subtitle(sub_maker=sub_maker, text=text_zh, subtitle_file=subtitle_file)
                audio_duration = vs.get_audio_duration(sub_maker)
                self.assertGreater(audio_duration, 0)
            else:
                self.fail("siliconflow invalid voice name")

        self.loop.run_until_complete(_do())
    
    @unittest.skipUnless(
        RUN_INTEGRATION_TESTS,
        "MPT_RUN_INTEGRATION_TESTS not set",
    )
    def test_azure_tts_v1(self):
        voice_name = "zh-CN-XiaoyiNeural-Female"
        voice_name = vs.parse_voice_name(voice_name)

        voice_file = f"{temp_dir}/tts-azure-v1-{voice_name}.mp3"
        subtitle_file = f"{temp_dir}/tts-azure-v1-{voice_name}.srt"
        sub_maker = vs.azure_tts_v1(
            text=text_zh, voice_name=voice_name, voice_file=voice_file, voice_rate=voice_rate
        )
        if not sub_maker:
            self.fail("azure tts v1 failed")
        vs.create_subtitle(sub_maker=sub_maker, text=text_zh, subtitle_file=subtitle_file)
        audio_duration = vs.get_audio_duration(sub_maker)
        self.assertGreater(audio_duration, 0)




    @unittest.skipUnless(
        RUN_INTEGRATION_TESTS,
        "MPT_RUN_INTEGRATION_TESTS not set",
    )
    def test_azure_tts_v2(self):
        if not vs.config.azure.get("speech_key") or not vs.config.azure.get("speech_region"):
            self.skipTest("Azure speech key or region is not configured")

        voice_name = "zh-CN-XiaoxiaoMultilingualNeural-V2-Female"
        voice_name = vs.parse_voice_name(voice_name)

        async def _do():
            voice_file = f"{temp_dir}/tts-azure-v2-{voice_name}.mp3"
            subtitle_file = f"{temp_dir}/tts-azure-v2-{voice_name}.srt"
            sub_maker = vs.azure_tts_v2(
                text=text_zh,
                voice_name=voice_name,
                voice_file=voice_file,
                voice_rate=1.0,
            )
            if not sub_maker:
                self.fail("azure tts v2 failed")
            vs.create_subtitle(sub_maker=sub_maker, text=text_zh, subtitle_file=subtitle_file)
            audio_duration = vs.get_audio_duration(sub_maker)
            self.assertGreater(audio_duration, 0)

        self.loop.run_until_complete(_do())
















    def _make_broken_clip_class(self, close_calls: list):
        """Return a clip class whose .duration raises and whose .close() records calls."""

        class _BrokenClip:
            @property
            def duration(self):
                raise RuntimeError("FFmpeg probe failed")

            def close(self):
                close_calls.append(True)

        return _BrokenClip




    def test_generate_subtitle_keeps_edge_provider_for_gemini_legacy_submaker(self):
        """
        验证 Gemini TTS 返回的 legacy 字幕结构在 edge provider 下可以直接产出
        SRT，不会因为匹配失败而回退到 Whisper。
        """
        script = "Gemini subtitle generation should work now. Testing multiple lines."
        sub_maker = vs.populate_legacy_submaker_with_full_text(
            vs.ensure_legacy_submaker_fields(vs.SubMaker()),
            script,
            2.4,
        )

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            task_service.config,
            "app",
            dict(task_service.config.app, subtitle_provider="edge"),
        ), patch("app.services.subtitle.create") as whisper_create, patch(
            "app.utils.utils.task_dir",
            lambda tid="": str(Path(tmp_dir) / tid) if tid else str(Path(tmp_dir)),
        ):
            task_id = "gemini-subtitle-edge-task"
            Path(tmp_dir, task_id).mkdir(parents=True, exist_ok=True)
            subtitle_path = task_service.generate_subtitle(
                task_id=task_id,
                params=type("Params", (), {"subtitle_enabled": True})(),
                video_script=script,
                sub_maker=sub_maker,
                audio_file="",
            )

            self.assertTrue(subtitle_path.endswith("subtitle.srt"))
            self.assertTrue(Path(subtitle_path).exists())
            self.assertFalse(whisper_create.called)
            subtitle_content = Path(subtitle_path).read_text(encoding="utf-8")
            self.assertIn("Gemini subtitle generation should work now", subtitle_content)
            self.assertIn("Testing multiple lines", subtitle_content)

    def test_script_split_keeps_thousand_separator_comma(self):
        """
        Edge TTS 会把 "1,000 years" 作为连续文本返回。脚本断句时不能把
        数字中间的英文逗号当成句子边界，否则字幕聚合会出现 issue #894
        里的 sub_items 数量少于 script_lines，并错误回退 Whisper。
        """
        text = (
            "It takes about 1,000 years for a single drop of water to finish "
            "the whole trip!"
        )

        self.assertEqual(
            utils.split_string_by_punctuations(text),
            [
                (
                    "It takes about 1,000 years for a single drop of water to finish "
                    "the whole trip"
                )
            ],
        )

    def test_edge_cue_aggregation_handles_thousand_separator_comma(self):
        """
        复现 issue #894 的关键形态：Edge cues 中最后一句作为连续文本返回，
        包含 `1,000 years`。脚本断句必须与 cues 聚合结果一致，不能把它
        拆成两条字幕。
        """
        text = (
            "The ocean isn't just sitting stil, it moves around the world like a massive "
            "amusement park ride! Cold water at the North and South Poles sinks to the "
            "bottom because it is heavy and salty. At the same time, warm water from the "
            "sunny equator flows along the top to take its place. This creates a giant "
            "underwater conveyor belt that travels all the way around the Earth. It takes "
            "about 1,000 years for a single drop of water to finish the whole trip!"
        )
        script_lines = utils.split_string_by_punctuations(text)
        cues = []
        for index, line in enumerate(script_lines):
            # Edge 的 cue content 经常没有脚本里的空格和标点布局，这里去掉空格
            # 来模拟更严格的匹配场景。
            cues.append(
                SimpleNamespace(
                    content=line.replace(" ", ""),
                    start=timedelta(seconds=index),
                    end=timedelta(seconds=index + 0.8),
                )
            )
        sub_maker = SimpleNamespace(cues=cues)

        sub_items = vs._build_subtitle_items_from_edge_cues(sub_maker, script_lines)

        self.assertEqual(len(sub_items), len(script_lines))
        self.assertIn("1,000 years", sub_items[-1])

    def test_script_split_keeps_clock_time_colon(self):
        """
        Edge TTS returns a clock time such as "10:30" as one word, so the script split
        must not break a line at its colon.
        """
        text = "The class starts at 10:30 every morning. We film everything in 16:9."

        self.assertEqual(
            utils.split_string_by_punctuations(text),
            ["The class starts at 10:30 every morning", "We film everything in 16:9"],
        )

    def test_edge_cue_aggregation_handles_clock_time(self):
        """
        The word boundaries edge-tts 7.3.1 returns for this script with en-US-JennyNeural:
        "10:30" is one word, "16:9" is three. Both lines must still get a subtitle each,
        without falling back to Whisper.
        """
        text = "We film everything in 16:9. The class starts at 10:30 every morning."
        script_lines = utils.split_string_by_punctuations(text)
        words = "We film everything in 16 : 9 The class starts at 10:30 every morning".split()
        cues = [
            SimpleNamespace(
                content=word,
                start=timedelta(seconds=index * 0.3),
                end=timedelta(seconds=index * 0.3 + 0.25),
            )
            for index, word in enumerate(words)
        ]

        sub_items = vs._build_subtitle_items_from_edge_cues(
            SimpleNamespace(cues=cues), script_lines
        )

        self.assertEqual(len(sub_items), len(script_lines))
        self.assertIn("10:30 every morning", sub_items[-1])

    def test_script_split_keeps_fullwidth_separators_between_digits(self):
        """
        Chinese and Japanese scripts often write times, scores and numbers with the
        full-width "：", "，" or "、". Edge TTS (zh-CN-XiaoxiaoNeural) returns "10：30", "3：2",
        "1，299元" and "第1、2" as one word each, so the script split must not break a line
        inside them.
        """
        text = "会议在10：30开始，请准时参加。比分是3：2，价格是1，299元。第1、2名都是中国选手。"

        self.assertEqual(
            utils.split_string_by_punctuations(text),
            [
                "会议在10：30开始",
                "请准时参加",
                "比分是3：2",
                "价格是1，299元",
                "第1、2名都是中国选手",
            ],
        )

    def test_edge_cue_aggregation_handles_fullwidth_separators_between_digits(self):
        """
        The word boundaries edge-tts 7.3.1 returns for this script with
        zh-CN-XiaoxiaoNeural: "10：30", "1，299元" and "第1、2" are one word each.
        Every line must still get its own subtitle.
        """
        text = "会议在10：30开始，请准时参加。价格是1，299元。第1、2名都是中国选手。"
        script_lines = utils.split_string_by_punctuations(text)
        words = [
            *"会议 在 10：30 开始 请 准时 参加".split(),
            *"价格 是 1，299元".split(),
            *"第1、2 名都 是 中国 选手".split(),
        ]
        cues = [
            SimpleNamespace(
                content=word,
                start=timedelta(seconds=index * 0.3),
                end=timedelta(seconds=index * 0.3 + 0.25),
            )
            for index, word in enumerate(words)
        ]

        sub_items = vs._build_subtitle_items_from_edge_cues(
            SimpleNamespace(cues=cues), script_lines
        )

        self.assertEqual(len(sub_items), len(script_lines))
        self.assertIn("会议在10：30开始", sub_items[0])
        self.assertIn("价格是1，299元", sub_items[2])
        self.assertIn("第1、2名都是中国选手", sub_items[3])

    def test_script_split_keeps_dots_inside_abbreviations_and_names(self):
        """A dot between two letters belongs to "U.S.", "e.g." or "example.com", not a line break."""
        text = (
            "The U.S. economy grew. Visit example.com for the details, e.g. the prices."
        )

        self.assertEqual(
            utils.split_string_by_punctuations(text),
            [
                "The U.S",
                "economy grew",
                "Visit example.com for the details",
                "e.g",
                "the prices",
            ],
        )

    def test_script_split_breaks_cjk_sentences_at_half_width_full_stops(self):
        """
        A Chinese or Japanese sentence ended with "." instead of "。" is still a
        sentence end, unlike the dot inside "U.S." or "example.com".
        """
        text = "今天天气很好.我们去公园散步.然后一起吃午饭.美国U.S.经济增长了.今日はいい天気です.公園に行きます."

        self.assertEqual(
            utils.split_string_by_punctuations(text),
            [
                "今天天气很好",
                "我们去公园散步",
                "然后一起吃午饭",
                "美国U.S",
                "经济增长了",
                "今日はいい天気です",
                "公園に行きます",
            ],
        )

    def test_edge_cue_aggregation_handles_dotted_abbreviations(self):
        """
        The word boundaries edge-tts 7.3.1 returns for each of these sentences with
        en-US-AriaNeural: "U.S.", "9 a.m." and "example.com" are one word each. Every line
        must still get its own subtitle, without falling back to Whisper.
        """
        text = (
            "The U.S. economy grew last year. Dr. Smith arrives at 9 a.m. sharp. "
            "Visit example.com for the details."
        )
        script_lines = utils.split_string_by_punctuations(text)
        words = [
            *"The U.S. economy grew last year Dr. Smith arrives at".split(),
            "9 a.m.",
            *"sharp Visit example.com for the details".split(),
        ]
        cues = [
            SimpleNamespace(
                content=word,
                start=timedelta(seconds=index * 0.3),
                end=timedelta(seconds=index * 0.3 + 0.25),
            )
            for index, word in enumerate(words)
        ]

        sub_items = vs._build_subtitle_items_from_edge_cues(
            SimpleNamespace(cues=cues), script_lines
        )

        self.assertEqual(len(sub_items), len(script_lines))
        self.assertIn("Smith arrives at 9 a.m", sub_items[-3])
        self.assertIn("Visit example.com for the details", sub_items[-1])

    def test_script_split_keeps_dots_between_letters_and_digits(self):
        """
        Edge TTS usually returns "No.1", "Vol.2", "Fig.3" and the full-width "ＮＯ.1" as one
        word, so a dot between a letter and a digit is no line break. A dot followed by a
        space still ends the sentence, and so does a dot right after a Chinese character, as
        in "很好.2025年".
        """
        self.assertEqual(
            utils.split_string_by_punctuations(
                "这款手机销量No.1，值得购买。我们发布了Vol.2版本。全网销量ＮＯ.1。"
                "今天天气很好.2025年会更好."
            ),
            [
                "这款手机销量No.1",
                "值得购买",
                "我们发布了Vol.2版本",
                "全网销量ＮＯ.1",
                "今天天气很好",
                "2025年会更好",
            ],
        )
        self.assertEqual(
            utils.split_string_by_punctuations(
                "Our brand is No.1 in sales. 3 stores opened this year. "
                "Fig.3 shows version 2.0 of the app."
            ),
            [
                "Our brand is No.1 in sales",
                "3 stores opened this year",
                "Fig.3 shows version 2.0 of the app",
            ],
        )

    def test_edge_cue_aggregation_handles_dots_between_letters_and_digits(self):
        """
        The word boundaries edge-tts 7.3.1 returns for this script with
        zh-CN-XiaoxiaoNeural: "No.1" and "Vol.2" are one word each. Every line must
        still get its own subtitle.
        """
        text = "这款手机销量No.1，值得购买。我们发布了Vol.2版本，欢迎体验。"
        script_lines = utils.split_string_by_punctuations(text)
        words = "这 款 手机 销量 No.1 值得 购买 我们 发布 了 Vol.2 版本 欢迎 体验".split()
        cues = [
            SimpleNamespace(
                content=word,
                start=timedelta(seconds=index * 0.3),
                end=timedelta(seconds=index * 0.3 + 0.25),
            )
            for index, word in enumerate(words)
        ]

        sub_items = vs._build_subtitle_items_from_edge_cues(
            SimpleNamespace(cues=cues), script_lines
        )

        self.assertEqual(len(sub_items), len(script_lines))
        self.assertIn("这款手机销量No.1", sub_items[0])
        self.assertIn("我们发布了Vol.2版本", sub_items[2])

    def test_script_split_supports_arabic_punctuation(self):
        """
        阿拉伯语脚本常用 ، ؛ ؟ 作为自然断句标点。断句阶段必须识别这些
        标点，否则 edge-tts cue 的停顿边界和脚本行边界会错位。
        """
        text = "مرحبا بالعالم، كيف حالك؟ هذا اختبار؛ يعمل بشكل جيد."

        self.assertEqual(
            utils.split_string_by_punctuations(text),
            [
                "مرحبا بالعالم",
                "كيف حالك",
                "هذا اختبار",
                "يعمل بشكل جيد",
            ],
        )

    def test_script_split_supports_native_full_stops(self):
        """
        Hindi and Bengali (danda), Urdu, Burmese, Khmer and Amharic end sentences
        with their own full stop. Without them the whole script stays one line.
        """
        cases = {
            "यह पहला वाक्य है। यह दूसरा वाक्य है॥ और यह तीसरा वाक्य है।": [
                "यह पहला वाक्य है",
                "यह दूसरा वाक्य है",
                "और यह तीसरा वाक्य है",
            ],
            "یہ پہلا جملہ ہے۔ یہ دوسرا جملہ ہے۔": [
                "یہ پہلا جملہ ہے",
                "یہ دوسرا جملہ ہے",
            ],
            "ဒါက ပထမ စာကြောင်း ဖြစ်ပါတယ်။ ဒါက ဒုတိယ စာကြောင်း ဖြစ်ပါတယ်။": [
                "ဒါက ပထမ စာကြောင်း ဖြစ်ပါတယ်",
                "ဒါက ဒုတိယ စာကြောင်း ဖြစ်ပါတယ်",
            ],
            "នេះជាប្រយោគទីមួយ។ នេះជាប្រយោគទីពីរ។": ["នេះជាប្រយោគទីមួយ", "នេះជាប្រយោគទីពីរ"],
            "ይህ የመጀመሪያው ዓረፍተ ነገር ነው። ይህ ሁለተኛው ዓረፍተ ነገር ነው።": [
                "ይህ የመጀመሪያው ዓረፍተ ነገር ነው",
                "ይህ ሁለተኛው ዓረፍተ ነገር ነው",
            ],
        }
        for text, expected_lines in cases.items():
            with self.subTest(text=text):
                self.assertEqual(
                    utils.split_string_by_punctuations(text), expected_lines
                )

    def test_edge_cue_aggregation_splits_sentences_at_native_full_stops(self):
        """
        Word boundaries edge-tts 7.3.1 returns for these scripts: hi-IN-SwaraNeural
        leaves the danda out, am-ET-MekdesNeural attaches "።" to the last word.
        Each sentence must still get its own subtitle.
        """
        cases = [
            (
                "यह पहला वाक्य है। यह दूसरा वाक्य है। और यह तीसरा वाक्य है।",
                "यह पहला वाक्य है यह दूसरा वाक्य है और यह तीसरा वाक्य है".split(),
                ["यह पहला वाक्य है", "यह दूसरा वाक्य है", "और यह तीसरा वाक्य है"],
            ),
            (
                "ይህ የመጀመሪያው ዓረፍተ ነገር ነው። ይህ ሁለተኛው ዓረፍተ ነገር ነው።",
                "ይህ የመጀመሪያው ዓረፍተ ነገር ነው። ይህ ሁለተኛው ዓረፍተ ነገር ነው።".split(),
                ["ይህ የመጀመሪያው ዓረፍተ ነገር ነው", "ይህ ሁለተኛው ዓረፍተ ነገር ነው"],
            ),
        ]
        for text, words, expected_lines in cases:
            with self.subTest(text=text):
                script_lines = utils.split_string_by_punctuations(text)
                cues = [
                    SimpleNamespace(
                        content=word,
                        start=timedelta(seconds=index * 0.4),
                        end=timedelta(seconds=index * 0.4 + 0.3),
                    )
                    for index, word in enumerate(words)
                ]

                sub_items = vs._build_subtitle_items_from_edge_cues(
                    SimpleNamespace(cues=cues), script_lines
                )

                self.assertEqual(len(sub_items), len(expected_lines))
                for item, line in zip(sub_items, expected_lines):
                    self.assertIn(line, item)

    def test_script_split_supports_thai_and_lao_sentence_spaces(self):
        """
        Thai and Lao separate sentences with a space instead of a full stop. A space
        next to a number, a word in Latin letters, the repetition mark ๆ or the
        abbreviation mark ฯ is inside the sentence, and Korean keeps its lines.
        """
        coffee = (
            "กาแฟเป็นเครื่องดื่มที่ได้รับความนิยมทั่วโลก ทุกเช้าผู้คนนับล้านเริ่มต้นวันด้วยกาแฟหนึ่งแก้ว "
            "กาแฟช่วยให้ร่างกายตื่นตัวและมีสมาธิมากขึ้น แต่การดื่มมากเกินไปอาจทำให้นอนไม่หลับ"
        )
        cases = {
            coffee: [
                "กาแฟเป็นเครื่องดื่มที่ได้รับความนิยมทั่วโลก",
                "ทุกเช้าผู้คนนับล้านเริ่มต้นวันด้วยกาแฟหนึ่งแก้ว",
                "กาแฟช่วยให้ร่างกายตื่นตัวและมีสมาธิมากขึ้น",
                "แต่การดื่มมากเกินไปอาจทำให้นอนไม่หลับ",
            ],
            "เด็ก ๆ ชอบเล่นฟุตบอล ทุกวันหลังเลิกเรียน": [
                "เด็ก ๆ ชอบเล่นฟุตบอล",
                "ทุกวันหลังเลิกเรียน",
            ],
            "ราคา 100 บาท ถูกมาก ฉันใช้ iPhone ทุกวัน มันดีมาก": [
                "ราคา 100 บาท",
                "ถูกมาก",
                "ฉันใช้ iPhone ทุกวัน",
                "มันดีมาก",
            ],
            "กรุงเทพฯ เป็นเมืองหลวงของประเทศไทย  มีประชากรมากกว่าสิบล้านคน": [
                "กรุงเทพฯ เป็นเมืองหลวงของประเทศไทย",
                "มีประชากรมากกว่าสิบล้านคน",
            ],
            "ສະບາຍດີ ມື້ນີ້ອາກາດດີຫຼາຍ ພວກເຮົາໄປທ່ຽວກັນ": [
                "ສະບາຍດີ",
                "ມື້ນີ້ອາກາດດີຫຼາຍ",
                "ພວກເຮົາໄປທ່ຽວກັນ",
            ],
            "안녕하세요 오늘은 날씨가 좋네요": ["안녕하세요 오늘은 날씨가 좋네요"],
        }
        for text, expected_lines in cases.items():
            with self.subTest(text=text):
                self.assertEqual(
                    utils.split_string_by_punctuations(text), expected_lines
                )
        self.assertEqual(
            utils.split_string_by_punctuations(
                coffee, split_thai_and_lao_sentences=False
            ),
            [coffee],
        )

    def test_edge_cue_aggregation_splits_thai_and_lao_sentences_at_spaces(self):
        """
        Word boundaries edge-tts 7.3.1 returns for these scripts with
        th-TH-PremwadeeNeural and lo-LA-KeomanyNeural. The Thai words have no space
        in them, except "เด็ก ๆ", and the Lao words are the parts between the
        spaces. Each sentence must still get its own subtitle.
        """
        cases = [
            (
                "กาแฟเป็นเครื่องดื่มที่ได้รับความนิยมทั่วโลก ทุกเช้าผู้คนนับล้านเริ่มต้นวันด้วยกาแฟหนึ่งแก้ว "
                "กาแฟช่วยให้ร่างกายตื่นตัวและมีสมาธิมากขึ้น แต่การดื่มมากเกินไปอาจทำให้นอนไม่หลับ",
                [
                    *"กาแฟ เป็น เครื่อง ดื่ม ที่ ได้ รับ ความ นิยม ทั่ว โลก".split(),
                    *"ทุก เช้า ผู้คน นับ ล้าน เริ่มต้น วัน ด้วย กาแฟ หนึ่ง แก้ว".split(),
                    *"กาแฟ ช่วย ให้ ร่างกาย ตื่นตัว และ มี สมาธิ มาก ขึ้น".split(),
                    *"แต่ การ ดื่ม มาก เกิน ไป อาจ ทำ ให้ นอน ไม่ หลับ".split(),
                ],
                [
                    "กาแฟเป็นเครื่องดื่มที่ได้รับความนิยมทั่วโลก",
                    "ทุกเช้าผู้คนนับล้านเริ่มต้นวันด้วยกาแฟหนึ่งแก้ว",
                    "กาแฟช่วยให้ร่างกายตื่นตัวและมีสมาธิมากขึ้น",
                    "แต่การดื่มมากเกินไปอาจทำให้นอนไม่หลับ",
                ],
            ),
            (
                "เด็ก ๆ ชอบเล่นฟุตบอล ทุกวันหลังเลิกเรียน",
                ["เด็ก ๆ", *"ชอบ เล่น ฟุตบอล ทุก วัน หลัง เลิก เรียน".split()],
                ["เด็ก ๆ ชอบเล่นฟุตบอล", "ทุกวันหลังเลิกเรียน"],
            ),
            (
                "ราคา 100 บาท ถูกมาก ฉันใช้ iPhone ทุกวัน มันดีมาก",
                "ราคา 100 บาท ถูก มาก ฉัน ใช้ iPhone ทุก วัน มัน ดี มาก".split(),
                ["ราคา 100 บาท", "ถูกมาก", "ฉันใช้ iPhone ทุกวัน", "มันดีมาก"],
            ),
            (
                "ສະບາຍດີ ມື້ນີ້ອາກາດດີຫຼາຍ ພວກເຮົາໄປທ່ຽວກັນ",
                "ສະບາຍດີ ມື້ນີ້ອາກາດດີຫຼາຍ ພວກເຮົາໄປທ່ຽວກັນ".split(),
                ["ສະບາຍດີ", "ມື້ນີ້ອາກາດດີຫຼາຍ", "ພວກເຮົາໄປທ່ຽວກັນ"],
            ),
        ]
        for text, words, expected_lines in cases:
            with self.subTest(text=text):
                script_lines = utils.split_string_by_punctuations(text)
                cues = [
                    SimpleNamespace(
                        content=word,
                        start=timedelta(seconds=index * 0.4),
                        end=timedelta(seconds=index * 0.4 + 0.3),
                    )
                    for index, word in enumerate(words)
                ]

                sub_items = vs._build_subtitle_items_from_edge_cues(
                    SimpleNamespace(cues=cues), script_lines
                )

                self.assertEqual(len(sub_items), len(expected_lines))
                for item, line in zip(sub_items, expected_lines):
                    self.assertIn(line, item)

    def test_match_script_line_normalizes_arabic_letter_forms(self):
        """
        edge-tts 可能把阿拉伯语中的不同字母形态归一化，或返回带变音符号、
        Tatweel 的 cue 文本。匹配时应容错，但最终字幕仍保留原始脚本文案。
        """
        script_lines = ["أهلاً وسهلاً بك في المدرسة"]

        matched = vs._match_script_line(
            script_lines,
            "اهلا وسهلا بك في المدرسه",
            0,
        )

        self.assertEqual(matched, script_lines[0])

    def test_edge_cue_aggregation_handles_arabic_variant_forms(self):
        """
        复现阿拉伯语字幕失败的核心路径：脚本包含 أ/ة 等字母形态，edge cue
        返回 ا/ه 等归一化形态时，聚合仍应生成完整字幕，避免回退 Whisper。
        """
        text = "أهلاً وسهلاً بك في المدرسة؟ هذا اختبار رائع، شكراً لك."
        script_lines = utils.split_string_by_punctuations(text)
        cue_texts = [
            "اهلا وسهلا بك في المدرسه",
            "هذا اختبار رائع",
            "شكرا لك",
        ]
        sub_maker = SimpleNamespace(
            cues=[
                SimpleNamespace(
                    content=cue_text,
                    start=timedelta(seconds=index),
                    end=timedelta(seconds=index + 0.8),
                )
                for index, cue_text in enumerate(cue_texts)
            ]
        )

        sub_items = vs._build_subtitle_items_from_edge_cues(sub_maker, script_lines)

        self.assertEqual(len(sub_items), len(script_lines))
        self.assertIn("أهلاً وسهلاً بك في المدرسة", sub_items[0])
        self.assertIn("شكراً لك", sub_items[-1])

    def test_create_subtitle_ignores_markdown_separator_lines(self):
        """
        用户手动脚本可能包含 `---` 这类 Markdown 分隔符。TTS 不会朗读
        这些符号行，字幕聚合也不应把它们当成目标字幕行，否则后续真实
        字幕会卡住并回退到 Whisper。
        """
        text = "第一段\n---\n第二段"
        sub_maker = SimpleNamespace(
            cues=[
                SimpleNamespace(
                    content="第一段",
                    start=timedelta(seconds=0),
                    end=timedelta(seconds=0.8),
                ),
                SimpleNamespace(
                    content="第二段",
                    start=timedelta(seconds=1),
                    end=timedelta(seconds=1.8),
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            subtitle_file = Path(tmp_dir) / "subtitle.srt"
            vs.create_subtitle(
                sub_maker=sub_maker,
                text=text,
                subtitle_file=str(subtitle_file),
            )

            subtitle_content = subtitle_file.read_text(encoding="utf-8")

        self.assertIn("第一段", subtitle_content)
        self.assertIn("第二段", subtitle_content)
        self.assertNotIn("---", subtitle_content)
        self.assertNotIn("00:00:00,000 --> 00:00:00,000", subtitle_content)

    def test_create_subtitle_word_level_preserves_edge_cue_timing(self):
        """Edge TTS 的细粒度 cue 应逐项写入，不能再被按标点聚合。"""
        sub_maker = SimpleNamespace(
            cues=[
                SimpleNamespace(
                    content="人工智能",
                    start=timedelta(seconds=0.1),
                    end=timedelta(seconds=0.8),
                ),
                SimpleNamespace(
                    content="正在",
                    start=timedelta(seconds=0.9),
                    end=timedelta(seconds=1.2),
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            subtitle_file = Path(tmp_dir) / "word-level.srt"
            vs.create_subtitle(
                sub_maker=sub_maker,
                text="人工智能正在发展。",
                subtitle_file=str(subtitle_file),
                word_level=True,
            )
            subtitle_content = subtitle_file.read_text(encoding="utf-8")

        self.assertIn("00:00:00,100 --> 00:00:00,800", subtitle_content)
        self.assertIn("人工智能", subtitle_content)
        self.assertIn("00:00:00,900 --> 00:00:01,200", subtitle_content)
        self.assertIn("正在", subtitle_content)

    def test_create_subtitle_word_level_falls_back_to_provider_granularity(self):
        """
        旧版 SubMaker 没有 cue 时，应保留语音服务返回的原始时间粒度。

        ElevenLabs、Fish Audio 等服务可能只返回短语或整句时间轴。此时不能
        按字符平均拆分并伪造逐词精度，否则字幕会逐渐偏离真实语音。
        """
        sub_maker = SimpleNamespace(
            cues=[],
            subs=["Hello world"],
            # 旧版 SubMaker 的 offset 使用 100 纳秒为单位的整数时间戳。
            offset=[(2_000_000, 11_000_000)],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            subtitle_file = Path(tmp_dir) / "word-level-fallback.srt"
            vs.create_subtitle(
                sub_maker=sub_maker,
                text="Hello world",
                subtitle_file=str(subtitle_file),
                word_level=True,
            )
            subtitle_content = subtitle_file.read_text(encoding="utf-8")

        self.assertEqual(subtitle_content.count(" --> "), 1)
        self.assertIn("00:00:00,200 --> 00:00:01,100", subtitle_content)
        self.assertIn("Hello world", subtitle_content)

    def test_create_subtitle_ignores_markdown_underscore_marks(self):
        """
        `_` 常被用户用作 Markdown 强调标记，但 TTS 返回的 cue 通常不包含
        这些格式符。匹配时应忽略 `_`，避免生成空字幕或回退到 Whisper。
        """
        text = "这是_a_测试。"
        sub_maker = SimpleNamespace(
            cues=[
                SimpleNamespace(
                    content="这是a测试",
                    start=timedelta(seconds=0),
                    end=timedelta(seconds=0.8),
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            subtitle_file = Path(tmp_dir) / "subtitle.srt"
            vs.create_subtitle(
                sub_maker=sub_maker,
                text=text,
                subtitle_file=str(subtitle_file),
            )

            subtitle_content = subtitle_file.read_text(encoding="utf-8")

        self.assertIn("这是a测试", subtitle_content)
        self.assertNotIn("这是_a_测试", subtitle_content)
        self.assertNotIn("00:00:00,000 --> 00:00:00,000", subtitle_content)





def _write_test_wav(filepath: str, duration_seconds: float = 1.0, sample_rate: int = 24000) -> str:
    import wave
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(round(duration_seconds * sample_rate))
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)
    return filepath




if __name__ == "__main__":
    # python -m unittest test.services.test_voice.TestVoiceService.test_azure_tts_v1
    # python -m unittest test.services.test_voice.TestVoiceService.test_azure_tts_v2
    unittest.main()
