import itertools
import math
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
import wave
from typing import Union
from xml.sax.saxutils import unescape

import requests
from loguru import logger

from app.utils.request_logging import trace_http_call
from moviepy.audio.io.AudioFileClip import AudioFileClip

from app.config import config
from app.services.utils.submaker import SubMaker
from app.services import bgm
from app.utils import utils
from app.utils.subtitle_reader import moviepy_subtitles
from app.utils.subtitle_writer import staged_subtitle_file

_DEFAULT_TTS_FFMPEG_TIMEOUT_SECONDS = 600
NO_VOICE_NAME = "no-voice"
# `none` 是 PR #981 里曾使用过的无配音标识。这里短期兼容这个值，避免
# 已经手动调用过该分支的 API 用户升级后立即失效；WebUI 和新代码统一使用
# 更明确的 `no-voice`。
_NO_VOICE_ALIASES = {NO_VOICE_NAME, "none"}


def _configure_pydub_ffmpeg(audio_segment_cls):
    configured_ffmpeg = utils.get_ffmpeg_binary()
    if configured_ffmpeg:
        audio_segment_cls.converter = configured_ffmpeg


def mktimestamp(time_unit: float) -> str:
    """
    Ubah satuan waktu 100 nanodetik (dipakai SubMaker) menjadi timestamp subtitle.

    Jalur subtitle lama dan timeline yang dibuat manual (misalnya dari teks penuh
    VoiceStudio) memakai fungsi pemformat ini.
    """
    # Bulatkan ke milidetik dulu, baru pecah menjadi jam/menit/detik. Memformat detik
    # sisa dengan `:06.3f` membuat 59,9996 detik tampil sebagai `00:00:60.000`, dan
    # parser SRT yang ketat menolak timestamp itu.
    total_milliseconds = int(round(time_unit / 10**4))
    hour, remainder = divmod(total_milliseconds, 3_600_000)
    minute, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hour:02d}:{minute:02d}:{seconds:02d}.{milliseconds:03d}"




















VOICESTUDIO_DEFAULT_BASE_URL = "http://localhost:3900"
VOICESTUDIO_DEFAULT_MODEL = "tts-1"
VOICESTUDIO_DEFAULT_VOICE = "default"


def get_voicestudio_base_url() -> str:
    """URL dasar server VoiceStudio (tanpa /v1)."""
    configured = str(config.voicestudio.get("base_url") or "").strip().rstrip("/")
    return configured or VOICESTUDIO_DEFAULT_BASE_URL


def is_voicestudio_voice(voice_name: str | None) -> bool:
    return (voice_name or "").startswith("voicestudio:")


def get_voicestudio_voices(*, fallback: bool = True) -> list[str]:
    """Daftar suara dari VoiceStudio (GET /v1/audio/voices); manual `voices` didahulukan."""
    configured = config.voicestudio.get("voices")
    if isinstance(configured, str):
        configured = configured.split(",")
    voices = []
    for entry in configured or []:
        name = str(entry).strip().removeprefix("voicestudio:").strip()
        if name and f"voicestudio:{name}" not in voices:
            voices.append(f"voicestudio:{name}")
    if not voices:
        try:
            response = trace_http_call(
                "GET", requests.get,
                f"{get_voicestudio_base_url()}/v1/audio/voices", timeout=5,
            )
            if response.status_code == 200:
                for item in response.json().get("voices", []):
                    name = str(item.get("voice_id") or item.get("id") or "").strip()
                    if name and f"voicestudio:{name}" not in voices:
                        voices.append(f"voicestudio:{name}")
            else:
                logger.warning(f"voicestudio voices request failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"voicestudio voice list unavailable ({type(e).__name__})")
    return voices or (
        [f"voicestudio:{VOICESTUDIO_DEFAULT_VOICE}"] if fallback else []
    )












def parse_voice_name(name: str):
    # zh-CN-XiaoyiNeural-Female
    # zh-CN-YunxiNeural-Male
    # zh-CN-XiaoxiaoMultilingualNeural-V2-Female
    name = name.strip()
    # Qualified IDs belong to their provider. Gender/style display labels are
    # parsed by each provider adapter, not rewritten inside an opaque voice ID.
    if ":" not in name:
        name = name.removesuffix("-Female").removesuffix("-Male")
    return name




























def is_no_voice(voice_name: str | None) -> bool:
    """
    判断用户是否明确选择了“无配音”模式。

    这里刻意不把空字符串当成无配音：空 voice 更可能是配置损坏、旧版本
    WebUI 状态丢失或接口参数缺失。只有明确的 sentinel 才进入静音分支，
    这样可以避免把真实错误伪装成正常生成。
    """
    return str(voice_name or "").strip().lower() in _NO_VOICE_ALIASES




def estimate_no_voice_duration(text: str) -> float:
    """
    为无配音模式估算一个稳定的视频时间轴长度。

    无配音仍需要一个音频占位来驱动现有素材裁剪、字幕时间轴和最终合成。
    估算策略尽量简单：
    1. 中文等 CJK 字符按约 4.2 字/秒估算；
    2. 英文/数字按约 2.7 词/秒估算；
    3. 其他语种文字按约 4.0 字符/秒兜底估算，覆盖俄语、阿拉伯语、
       日文假名、韩文等非 ASCII 文本；
    4. 每个断句补一点停顿，让字幕切换不至于过于紧凑；
    5. 最少 3 秒，避免极短脚本生成 0 秒音频。
    """
    normalized_text = (text or "").strip()
    if not normalized_text:
        return 3.0

    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", normalized_text))
    words = len(re.findall(r"[A-Za-z0-9]+", normalized_text))
    ascii_word_chars = sum(len(word) for word in re.findall(r"[A-Za-z0-9]+", normalized_text))
    other_text_chars = 0
    for char in normalized_text:
        # Unicode category 以 L 开头表示各语种字母，N 表示数字。前面已经单独
        # 统计了 CJK 和 ASCII 单词，这里只统计剩余文字，避免英文被重复计时。
        category = unicodedata.category(char)
        if category.startswith(("L", "N")):
            other_text_chars += 1
    other_text_chars = max(other_text_chars - cjk_chars - ascii_word_chars, 0)
    sentence_count = max(len(utils.split_string_by_punctuations(normalized_text)), 1)

    cjk_duration = cjk_chars / 4.2
    word_duration = words / 2.7
    other_text_duration = other_text_chars / 4.0
    pause_duration = max(sentence_count - 1, 0) * 0.35
    return max(3.0, cjk_duration + word_duration + other_text_duration + pause_duration)


def generate_silent_audio(duration_seconds: float, output_file: str) -> bool:
    """
    生成静音音频。

    支持直接生成 16-bit mono PCM WAV 音频（精准到单个样本，无编码延迟），
    或通过 FFmpeg anullsrc 生成 MP3 音频（作为“无配音”模式的占位）。
    """
    ensure_file_path_exists(output_file)
    duration_seconds = max(
        float(duration_seconds or 0), utils.MIN_PAUSE_DURATION_SECONDS
    )

    if output_file.lower().endswith(".wav"):
        sample_rate = 24000
        num_samples = int(round(duration_seconds * sample_rate))
        with wave.open(output_file, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * num_samples)
        return os.path.exists(output_file) and os.path.getsize(output_file) > 0

    ffmpeg_binary = utils.get_ffmpeg_binary()
    command = [
        ffmpeg_binary,
        "-nostdin",
        "-v",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-t",
        f"{duration_seconds:.3f}",
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "4",
    ]

    logger.info(
        f"generating silent audio for no-voice mode, duration: {duration_seconds:.2f}s"
    )
    return _publish_tts_ffmpeg_output(command, output_file, "silent narration encode")


def _single_tts(
    text: str,
    voice_name: str,
    voice_rate: float,
    voice_file: str,
    voice_volume: float = 1.0,
) -> Union[SubMaker, None]:
    if is_no_voice(voice_name):
        duration_seconds = estimate_no_voice_duration(text)
        if not generate_silent_audio(duration_seconds, voice_file):
            return None

        sub_maker = ensure_legacy_submaker_fields(SubMaker())
        return populate_legacy_submaker_with_full_text(
            sub_maker=sub_maker,
            text=text,
            audio_duration_seconds=duration_seconds,
        )

    if is_voicestudio_voice(voice_name):
        # Format: voicestudio:<voice_id>; sufiks -Female/-Male hanya label tampilan.
        voice_id = voice_name.split(":", 1)[1].strip()
        if voice_id.endswith(("-Female", "-Male")):
            voice_id = voice_id.rsplit("-", 1)[0]
        if not voice_id:
            logger.error(f"Invalid voicestudio voice name format: {voice_name}")
            return None
        return voicestudio_tts(text, voice_id, voice_file, voice_rate, voice_volume)

    logger.error(
        f"Unsupported voice name '{voice_name}'. Only VoiceStudio voices "
        "(voicestudio:<voice>) are supported."
    )
    return None


def _run_tts_ffmpeg(command: list[str], stage: str):
    """Bound TTS FFmpeg work and reap the child on timeout."""
    raw_timeout = config.app.get(
        "ffmpeg_tts_timeout_seconds",
        _DEFAULT_TTS_FFMPEG_TIMEOUT_SECONDS,
    )
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError("ffmpeg_tts_timeout_seconds must be positive") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("ffmpeg_tts_timeout_seconds must be positive")

    try:
        # subprocess.run kills and waits for the child on timeout. Do not allow
        # FFmpeg to wait for terminal input in an unattended generation task.
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg {stage} timed out after {timeout:g} seconds")
    except OSError as exc:
        logger.error(f"failed to start FFmpeg {stage}: {exc}")
    return None


def _publish_tts_ffmpeg_output(
    command: list[str], output_file: str, stage: str
) -> bool:
    """Encode beside the destination and replace only after a complete output."""
    output_dir = os.path.dirname(output_file) or "."
    with tempfile.TemporaryDirectory(
        prefix=".mpt-tts-audio-", dir=output_dir
    ) as publish_temp:
        staged_output = os.path.join(
            publish_temp, f"narration{os.path.splitext(output_file)[1] or '.mp3'}"
        )
        result = _run_tts_ffmpeg([*command, staged_output], stage)
        if result is None:
            return False
        if result.returncode != 0:
            logger.error(
                f"FFmpeg {stage} failed: "
                f"{(result.stderr or result.stdout or '').strip()}"
            )
            return False
        if not os.path.exists(staged_output) or os.path.getsize(staged_output) == 0:
            logger.error(f"FFmpeg {stage} produced no narration audio")
            return False
        try:
            os.replace(staged_output, output_file)
        except OSError as exc:
            logger.error(f"failed to publish {stage} audio: {exc}")
            return False
        return True



def apply_audio_volume(audio_file: str, output_file: str, volume: float) -> bool:
    """Encode narration export gain to a caller-owned destination."""
    if not math.isfinite(volume) or volume < 0:
        raise ValueError("audio export volume must be finite and nonnegative")
    ensure_file_path_exists(output_file)
    command = [
        utils.get_ffmpeg_binary(), "-nostdin", "-v", "error", "-y",
        "-i", audio_file, "-vn", "-af", f"volume={volume}",
        "-codec:a", "libmp3lame", "-q:a", "4",
    ]
    return _publish_tts_ffmpeg_output(command, output_file, "audio export volume")

def _concat_audio_files(audio_files: list[str], output_file: str) -> bool:
    """
    使用 PCM 解码与统一重编码合并多个音频分段。

    将所有输入分段统一转换为标准 PCM (24000Hz 16-bit mono) 样本进行无缝拼接，
    最后一次性编码为目标文件（如 MP3），彻底解决因每个 MP3 片段编码器延迟与填充（delay/padding）
    累积而导致的音画不同步及字幕漂移问题。
    """
    if not audio_files:
        return False
    ensure_file_path_exists(output_file)
    if len(audio_files) == 1:
        if audio_files[0] != output_file:
            shutil.copyfile(audio_files[0], output_file)
        return True

    target_sample_rate = 24000
    ffmpeg_binary = utils.get_ffmpeg_binary()

    with tempfile.TemporaryDirectory() as concat_temp:
        temp_combined_wav = os.path.join(concat_temp, "combined_master.wav")
        combined_frames = 0
        with wave.open(temp_combined_wav, "wb") as combined_wave:
            combined_wave.setnchannels(1)
            combined_wave.setsampwidth(2)
            combined_wave.setframerate(target_sample_rate)

            def append_pcm(reader):
                nonlocal combined_frames
                chunk_frames = 0
                while chunk := reader.readframes(8192):
                    if len(chunk) % 2:
                        raise ValueError("incomplete PCM sample in narration chunk")
                    combined_wave.writeframesraw(chunk)
                    chunk_frames += len(chunk) // 2
                if not chunk_frames or chunk_frames != reader.getnframes():
                    raise ValueError("empty or truncated narration chunk")
                combined_frames += chunk_frames

            for idx, f in enumerate(audio_files):
                if not os.path.exists(f) or os.path.getsize(f) == 0:
                    logger.error(f"narration chunk is missing or empty: {f}")
                    return False

                # 检查是否已经是 24000Hz 16-bit mono WAV
                is_valid_pcm_wav = False
                if f.lower().endswith(".wav"):
                    try:
                        with wave.open(f, "rb") as wf:
                            if (
                                wf.getframerate() == target_sample_rate
                                and wf.getnchannels() == 1
                                and wf.getsampwidth() == 2
                            ):
                                is_valid_pcm_wav = True
                                append_pcm(wf)
                    except Exception as exc:
                        if is_valid_pcm_wav:
                            logger.error(f"failed to stream PCM input: {exc}")
                            return False
                        is_valid_pcm_wav = False

                if not is_valid_pcm_wav:
                    # 使用 FFmpeg 将输入文件解码为 24000Hz 16-bit mono PCM WAV
                    pcm_wav = os.path.join(concat_temp, f"chunk_{idx}.wav")
                    cmd = [
                        ffmpeg_binary,
                        "-nostdin",
                        "-v",
                        "error",
                        "-y",
                        "-i",
                        f,
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        str(target_sample_rate),
                        "-codec:a",
                        "pcm_s16le",
                        pcm_wav,
                    ]
                    res = _run_tts_ffmpeg(cmd, "pause audio decode")
                    if res is None:
                        return False
                    if res.returncode == 0 and os.path.exists(pcm_wav):
                        try:
                            with wave.open(pcm_wav, "rb") as wf:
                                append_pcm(wf)
                        except Exception as e:
                            logger.error(f"failed to read decoded pcm wav: {e}")
                            return False
                    else:
                        logger.error(f"failed to decode audio chunk with ffmpeg: {res.stderr}")
                        return False

        if not combined_frames:
            logger.error("no valid audio samples to concatenate")
            return False

        if output_file.lower().endswith(".wav"):
            shutil.copyfile(temp_combined_wav, output_file)
            return True

        command = [
            ffmpeg_binary,
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            temp_combined_wav,
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "4",
        ]
        return _publish_tts_ffmpeg_output(
            command, output_file, "pause audio encode"
        )




def tts(
    text: str,
    voice_name: str,
    voice_rate: float,
    voice_file: str,
    voice_volume: float = 1.0,
) -> Union[SubMaker, None]:
    # Emoji tidak dibacakan: sintesis suara akan melafalkan namanya ("chart
    # increasing"), dan tiap emoji menambah satu batas kata.
    narration = utils.remove_emoji(text)
    if narration != text and not narration.strip():
        logger.warning("the script has no text to narrate once emoji are removed")
        return None
    # Tag jeda [pause: ...] tidak didukung VoiceStudio; hapus sebelum sintesis.
    if utils.has_pause_tags(narration):
        narration = utils.remove_pause_tags(narration)
    return _single_tts(
        text=narration,
        voice_name=voice_name,
        voice_rate=voice_rate,
        voice_file=voice_file,
        voice_volume=voice_volume,
    )


def ensure_file_path_exists(file_path: str) -> None:
    """Pastikan direktori berkas keluaran ada, agar kegagalan path lokal tidak menutupi hasil TTS yang sebenarnya."""
    dir_path = os.path.dirname(file_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)


def ensure_legacy_submaker_fields(sub_maker: SubMaker) -> SubMaker:
    """
    Lengkapi field kompatibilitas untuk pemanggil yang masih memakai struktur subtitle lama.

    `SubMaker` terutama menyediakan `cues/get_srt()`, sedangkan jalur teks penuh
    (VoiceStudio, tanpa batas kata) masih membaca dan menulis `subs/offset`.
    """
    if not hasattr(sub_maker, "subs"):
        sub_maker.subs = []
    if not hasattr(sub_maker, "offset"):
        sub_maker.offset = []
    return sub_maker


def populate_legacy_submaker_with_full_text(
    sub_maker: SubMaker, text: str, audio_duration_seconds: float
) -> SubMaker:
    """
    Isi struktur subtitle lama `subs/offset` dengan teks penuh.

    Latar belakang:
    1. VoiceStudio tidak mengembalikan batas kata, tetapi alur berikutnya tetap
       butuh objek ber-`subs/offset` untuk menghitung durasi audio dan subtitle.
    2. Untuk TTS tanpa batas kata, teks setidaknya dipecah per kalimat naskah agar
       agregasi `subtitle_provider=edge` tetap dapat bekerja.

    Args:
        sub_maker: objek subtitle yang akan diisi field kompatibilitasnya
        text: teks naskah asli
        audio_duration_seconds: total durasi audio dalam detik

    Returns:
        SubMaker yang sudah terisi data subtitle kompatibel
    """
    sub_maker = ensure_legacy_submaker_fields(sub_maker)

    # Kosongkan nilai lama agar data tidak menumpuk bila objek dipakai ulang.
    sub_maker.subs = []
    sub_maker.offset = []

    # Pakai pembersihan naskah yang sama dengan create_subtitle(): baris pemisah
    # Markdown seperti `---` dan `***` tidak dibacakan; jika ikut dibagi menurut
    # proporsi karakter, baris itu memakan durasi audio sehingga subtitle
    # berikutnya muncul terlalu awal atau yang terakhir hilang sebelum audio selesai.
    normalized_text = utils.normalize_script_for_subtitle_matching(text or "").strip()
    if not normalized_text:
        return sub_maker

    audio_duration_100ns = max(int(audio_duration_seconds * 10000000), 1)

    # Bila batas kata tidak tersedia, pakai strategi lama: pecah menurut tanda
    # baca lalu bagi durasi sebanding jumlah karakter. Dengan begitu
    # create_subtitle() dapat mencocokkan kalimat naskah.
    sentences = utils.split_string_by_punctuations(normalized_text)
    if not sentences:
        sentences = [normalized_text]

    total_chars = sum(len(sentence) for sentence in sentences)
    if total_chars <= 0:
        sub_maker.subs.append(normalized_text)
        sub_maker.offset.append((0, audio_duration_100ns))
        return sub_maker

    current_offset = 0
    for index, sentence in enumerate(sentences):
        cleaned_sentence = sentence.strip()
        if not cleaned_sentence:
            continue

        # 前面的句子按字符数比例分配时长，最后一句兜底吃掉剩余时长，
        # 避免整数取整导致总时长丢失或字幕结束时间短于音频。
        if index == len(sentences) - 1:
            sentence_end = audio_duration_100ns
        else:
            sentence_chars = len(cleaned_sentence)
            sentence_duration = max(
                int(audio_duration_100ns * (sentence_chars / total_chars)),
                1,
            )
            sentence_end = min(current_offset + sentence_duration, audio_duration_100ns)

        sub_maker.subs.append(cleaned_sentence)
        sub_maker.offset.append((current_offset, sentence_end))
        current_offset = sentence_end

    return sub_maker


































def _validate_remote_tts_audio(file_path: str) -> None:
    """Decode accepted audio fully before replacing a successful narration.

    MoviePy's duration/initial frame probe does not validate later MP3 frames.
    Reuse the bounded, self-contained FFmpeg audio validator without following
    playlists or resubmitting an already accepted speech request.
    """
    try:
        bgm.validate_audio_file(file_path, timeout_seconds=120)
    except (bgm.BgmUploadError, bgm.BgmServiceError) as exc:
        raise ValueError("TTS returned audio that could not be fully decoded") from exc








def _openai_compatible_tts(
    provider: str,
    base_url: str,
    api_key: str,
    model_id: str,
    voice: str,
    text: str,
    voice_rate: float,
    voice_file: str,
) -> Union[SubMaker, None]:
    """Transport bersama untuk server ``/audio/speech`` kompatibel OpenAI
    (VoiceStudio).

    Menulis audio yang dikembalikan ke ``voice_file`` dan membuat SubMaker teks
    penuh: server ini tidak mengembalikan timestamp per kata, jadi atur
    ``subtitle_provider = "whisper"`` agar subtitle lebih selaras.
    """
    url = f"{base_url}/audio/speech"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model_id,
        "input": text,
        "voice": voice,
        "response_format": "mp3",
        # OpenAI speech API accepts speed 0.25-4.0; MoneyPrinterTurbo's rate is a
        # 1.0-centred multiplier, so it maps directly (clamped to the valid range).
        "speed": max(0.25, min(4.0, float(voice_rate or 1.0))),
    }
    # OpenAI speech 协议没有音量字段；最终混音阶段应用 voice_volume。
    # speed 仅调节语速，不能作为音量参数使用。

    for i in range(3):
        temporary_audio = None
        response_accepted = False
        try:
            logger.info(f"start {provider} tts, voice: {voice}, try: {i + 1}")
            ensure_file_path_exists(voice_file)

            response = trace_http_call(
                "POST", requests.post, url, json=payload, headers=headers, allow_redirects=False, timeout=120)
            if 300 <= response.status_code < 400:
                # Redirecting a speech POST may replay a billed synthesis or
                # forward its input/credentials. Do not follow or resubmit it.
                logger.error("TTS endpoint returned a redirect; stop speech retries")
                return None
            if response.status_code != 200:
                logger.error(
                    f"{provider} tts failed with status {response.status_code}: {response.text[:200]}"
                )
                continue

            response_accepted = True
            if not response.content:
                raise ValueError(f"{provider} returned empty audio")

            # 先写入同目录临时文件并真实解码，成功后才替换目标。失败不能破坏
            # 已有试听/配音；先关闭文件再解码和替换，兼容 Windows 文件占用规则。
            with tempfile.NamedTemporaryFile(
                dir=os.path.dirname(os.path.abspath(voice_file)),
                suffix=".mp3", delete=False,
            ) as f:
                temporary_audio = f.name
                f.write(response.content)

            _validate_remote_tts_audio(temporary_audio)
            audio_clip = AudioFileClip(temporary_audio)
            try:
                audio_duration = audio_clip.duration
            finally:
                audio_clip.close()
            if not math.isfinite(audio_duration) or audio_duration <= 0:
                raise ValueError(f"{provider} returned an invalid audio duration")

            sub_maker = ensure_legacy_submaker_fields(SubMaker())
            os.replace(temporary_audio, voice_file)
            logger.success(f"{provider} tts succeeded: {voice_file}")
            return populate_legacy_submaker_with_full_text(
                sub_maker=sub_maker,
                text=text,
                audio_duration_seconds=audio_duration,
            )
        except requests.exceptions.ConnectTimeout:
            # No connection was established; retrying cannot replay synthesis.
            logger.warning(f"{provider} tts could not connect, retrying")
        except requests.exceptions.RequestException as exc:
            # A lost response can follow successful remote synthesis. Keep the
            # same acceptance boundary as hosted speech providers: do not POST
            # again when the first request's outcome is unknown.
            logger.error(
                f"{provider} tts result is unconfirmed after a transport error; "
                f"stop speech retries: {type(exc).__name__}"
            )
            return None
        except Exception as e:
            logger.error(f"{provider} tts failed: {str(e)}")
            if response_accepted:
                # Retrying local processing cannot recover this accepted response
                # and would submit another synthesis request.
                return None
        finally:
            if temporary_audio and os.path.exists(temporary_audio):
                try:
                    os.unlink(temporary_audio)
                except OSError as exc:
                    # 清理失败仍保持 TTS 的失败返回约定，不用次要异常掩盖原始原因。
                    logger.warning(f"could not remove temporary {provider} audio: {exc}")

    return None






def voicestudio_tts(
    text: str,
    voice: str,
    voice_file: str,
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
) -> Union[SubMaker, None]:
    """Sintesis suara lewat server VoiceStudio lokal (API kompatibel OpenAI).

    VoiceStudio tidak mengembalikan timestamp per kata, jadi SubMaker hanya berisi
    teks penuh; atur ``subtitle_provider = "whisper"`` agar subtitle memakai ASR VoiceStudio.
    """
    text = (text or "").strip()
    if not text or not any(character.isalnum() for character in text):
        logger.error("VoiceStudio TTS text has no speakable characters")
        return None
    return _openai_compatible_tts(
        "voicestudio",
        f"{get_voicestudio_base_url()}/v1",
        "",
        str(config.voicestudio.get("model") or VOICESTUDIO_DEFAULT_MODEL),
        voice,
        text,
        voice_rate,
        voice_file,
    )














def _format_text(text: str) -> str:
    """
    Bersihkan teks naskah sebelum penyelarasan subtitle.

    Pembersihan tidak cukup dilakukan saat LLM membuat naskah, karena pengguna juga
    dapat menempel naskah sendiri atau mengirim teks ber-Markdown lewat API. TTS
    biasanya tidak membacakan baris pemisah seperti `---`, `___`, `***`, maupun
    penanda penekanan `_`; bila karakter itu tetap ada, `create_subtitle()`
    menunggu cue yang tidak pernah muncul sehingga berkas subtitle tidak jadi
    dibuat, atau koreksi ASR menghasilkan timeline serba nol.
    """
    text = utils.remove_pause_tags(text or "")
    text = text.replace("[", " ")
    text = text.replace("]", " ")
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = text.replace("{", " ")
    text = text.replace("}", " ")
    return utils.normalize_script_for_subtitle_matching(text)


def _build_subtitle_formatter():
    """
    Kembalikan fungsi pemformat baris SRT yang seragam.

    Dipisah agar jalur `cues` dan jalur lama `subs/offset` memakai format tulis
    subtitle yang sama, sehingga tidak muncul selisih format kecil di antara keduanya.
    """

    def formatter(idx: int, start_time: float, end_time: float, sub_text: str) -> str:
        start_t = mktimestamp(start_time).replace(".", ",")
        end_t = mktimestamp(end_time).replace(".", ",")
        return f"{idx}\n{start_t} --> {end_t}\n{sub_text}\n"

    return formatter


# Harakat Arab dan Tatweel dapat muncul pada teks hasil TTS/ASR. Karakter ini
# tidak mengubah makna, tetapi membuat pencocokan persis antara naskah dan cue gagal.
_ARABIC_DIACRITICS = re.compile("[\u0610-\u061A\u064B-\u065F\u0670\u0640\u06D6-\u06ED]")


def _normalize_arabic(text: str) -> str:
    """Seragamkan variasi huruf Arab yang umum agar cue subtitle lebih toleran saat dicocokkan dengan baris naskah.

    TTS/ASR dapat mengembalikan bentuk huruf Arab yang berbeda dari naskah, misalnya
    أ/إ/آ disatukan menjadi ا, atau menyertakan harakat. Fungsi ini hanya dipakai di
    lapisan pencocokan terakhir dan tidak mengubah teks subtitle yang ditampilkan.
    """
    text = _ARABIC_DIACRITICS.sub("", text)
    for src, dst in (
        ("أإآٱ", "ا"),
        ("ىئ", "ي"),
        ("ة", "ه"),
        ("ؤ", "و"),
    ):
        for ch in src:
            text = text.replace(ch, dst)
    return text


def _match_script_line(script_lines: list[str], current_text: str, sub_index: int) -> str:
    """
    尝试把当前累计的字幕文本，与脚本中的某一条标准断句匹配起来。

    这里复用了项目原有的“按标点拆脚本，再逐段比对”的思路：
    1. 优先精确匹配；
    2. 再做一次去标点和 Markdown `_` 格式符后的匹配；
    3. 最后做一次阿拉伯语字符形态归一化匹配。

    这样可以兼容：
    - TTS 返回里可能缺失或单独拆分的标点；
    - 中文场景下词边界和脚本文本不完全一一对应的情况。
    """
    if len(script_lines) <= sub_index:
        return ""

    target_line = script_lines[sub_index]
    comparison_target = unicodedata.normalize("NFC", target_line)
    current_text = unicodedata.normalize("NFC", current_text)
    if current_text == comparison_target:
        return target_line.strip()

    current_text_normalized = re.sub(r"[_\W]+", "", current_text)
    target_line_normalized = re.sub(r"[_\W]+", "", comparison_target)
    if current_text_normalized == target_line_normalized:
        return target_line.strip()

    # Toleransi terakhir untuk Arab: bentuk huruf, harakat, atau Tatweel pada hasil
    # TTS/ASR dapat berbeda dari naskah. Perbandingan ternormalisasi hanya dipakai
    # setelah pencocokan biasa gagal, sehingga teks non-Arab tidak terpengaruh.
    current_ar = re.sub(r"[_\W]+", "", _normalize_arabic(current_text))
    target_ar = re.sub(r"[_\W]+", "", _normalize_arabic(comparison_target))
    if current_ar and current_ar == target_ar:
        return target_line.strip()

    return ""


def _write_subtitle_items(sub_items: list[str], subtitle_file: str) -> bool:
    """Publish a complete, parseable SRT without destroying earlier captions."""
    try:
        ensure_file_path_exists(subtitle_file)
        with staged_subtitle_file(subtitle_file) as staged:
            with open(staged, "w", encoding="utf-8") as file:
                file.write("\n".join(sub_items) + "\n")
            sbs = moviepy_subtitles(staged)
            if not sbs:
                raise ValueError("subtitle output contains no cues")
            duration = max(tb for ((ta, tb), txt) in sbs)
            os.replace(staged, subtitle_file)
        logger.info(
            f"completed, subtitle file created: {subtitle_file}, duration: {duration}"
        )
        return True
    except Exception as e:
        logger.error(f"failed, error: {str(e)}")
        return False


def _build_subtitle_items_from_edge_cues(
    sub_maker: SubMaker, script_lines: list[str]
) -> list[str]:
    """
    Gabungkan `cues` halus dari SubMaker menjadi potongan SRT per kalimat naskah.

    Latar belakang:
    `SubMaker.get_srt()` condong menghasilkan timeline per kata/frasa. Untuk bahasa
    Inggris itu masih layak sebagai sorotan kata, tetapi bila subtitle video pendek
    berbahasa Mandarin disalin apa adanya, hasilnya terpecah seperti
    "uang / adalah / suatu / alat / sosial" dan sangat sulit dibaca.

    实现策略：
    1. 逐个消费 cues 中的 `content`；
    2. 累积成一段候选文本；
    3. 当候选文本与脚本里当前目标断句匹配时，收敛为一个完整字幕段；
    4. 使用第一条 cue 的开始时间和最后一条 cue 的结束时间，保证时间轴连续。
    """
    formatter = _build_subtitle_formatter()
    sub_items = []
    sub_index = 0
    current_text = ""
    current_start_time = None

    for cue in sub_maker.cues:
        cue_text = unescape(cue.content)
        if current_start_time is None:
            current_start_time = int(cue.start.total_seconds() * 10000000)

        current_end_time = int(cue.end.total_seconds() * 10000000)
        current_text += cue_text

        matched_text = _match_script_line(script_lines, current_text, sub_index)
        if not matched_text:
            continue

        sub_index += 1
        sub_items.append(
            formatter(
                idx=sub_index,
                start_time=current_start_time,
                end_time=current_end_time,
                sub_text=matched_text,
            )
        )
        current_text = ""
        current_start_time = None

    if current_text.strip():
        logger.warning(
            f"edge cues still have unmatched text after aggregation: {current_text}"
        )

    return sub_items


def _build_subtitle_items_from_legacy_submaker(
    sub_maker: SubMaker, script_lines: list[str]
) -> list[str]:
    """
    Gabungkan struktur lama `subs/offset` menjadi potongan SRT per kalimat naskah.

    Inti caranya tidak berubah; hanya dipisah menjadi fungsi sendiri agar berbagi
    pencocokan kalimat dan alur penulisan dengan penggabungan `cues`.
    """
    formatter = _build_subtitle_formatter()
    start_time = -1.0
    sub_items = []
    sub_index = 0
    sub_line = ""

    legacy_offsets = getattr(sub_maker, "offset", [])
    legacy_subs = getattr(sub_maker, "subs", [])
    for _, (offset, sub) in enumerate(zip(legacy_offsets, legacy_subs)):
        current_start_time, current_end_time = offset
        if start_time < 0:
            start_time = current_start_time

        sub_line += unescape(sub)
        matched_text = _match_script_line(script_lines, sub_line, sub_index)
        if not matched_text:
            continue

        sub_index += 1
        sub_items.append(
            formatter(
                idx=sub_index,
                start_time=start_time,
                end_time=current_end_time,
                sub_text=matched_text,
            )
        )
        start_time = -1.0
        sub_line = ""

    if sub_line.strip():
        logger.warning(
            f"legacy subtitle items still have unmatched text after aggregation: {sub_line}"
        )

    return sub_items


def _build_subtitle_items_from_edge_cues_words(sub_maker: SubMaker) -> list[str]:
    """
    Format langsung cue SubMaker menjadi item SRT per kata / per cue.
    """
    formatter = _build_subtitle_formatter()
    sub_items = []
    sub_index = 0
    for cue in sub_maker.cues:
        cue_text = unescape(cue.content).strip()
        if not cue_text:
            continue
        sub_index += 1
        start_time = int(cue.start.total_seconds() * 10000000)
        end_time = int(cue.end.total_seconds() * 10000000)
        sub_items.append(
            formatter(
                idx=sub_index,
                start_time=start_time,
                end_time=end_time,
                sub_text=cue_text,
            )
        )
    return sub_items


def _build_subtitle_items_from_legacy_submaker_words(sub_maker: SubMaker) -> list[str]:
    """
    Directly format legacy submaker into single-word SRT items.
    """
    formatter = _build_subtitle_formatter()
    sub_items = []
    sub_index = 0
    legacy_offsets = getattr(sub_maker, "offset", [])
    legacy_subs = getattr(sub_maker, "subs", [])
    for offset, sub in zip(legacy_offsets, legacy_subs):
        cue_text = unescape(sub).strip()
        if not cue_text:
            continue
        sub_index += 1
        start_time, end_time = offset
        sub_items.append(
            formatter(
                idx=sub_index,
                start_time=start_time,
                end_time=end_time,
                sub_text=cue_text,
            )
        )
    return sub_items


def _join_lines_split_inside_words(
    text: str, script_lines: list[str], words: list[str]
) -> list[str]:
    """
    Join each script line that ends inside a TTS word with the line after it.

    TTS dapat mengembalikan "July 20, 1969", "Washington, D.C.", "No. 1" and
    "Am 9. November 1989" as one word each, but the script split ends a line
    at their comma or full stop. No run of words can match such a line, and
    without it no subtitle file is written at all. A joined line keeps the
    script text between its parts, as in "On July 20, 1969". Lines are only
    joined when the words spell the script exactly, compared as in
    _match_script_line().
    """

    def comparable(value: str) -> str:
        return re.sub(r"[_\W]+", "", unicodedata.normalize("NFC", value))

    word_texts = [comparable(unescape(word)) for word in words]
    line_texts = [comparable(line) for line in script_lines]
    if "".join(word_texts) != "".join(line_texts):
        return script_lines

    word_ends = set(itertools.accumulate(map(len, word_texts)))
    line_ends = itertools.accumulate(map(len, line_texts))
    joined_lines = []
    start = None
    position = 0
    for line, line_end in zip(script_lines, line_ends):
        # Each script line is a part of text, in order.
        line_start = text.find(line, position)
        position = line_start + len(line)
        if start is None:
            start = line_start
        if line_end in word_ends:
            joined_lines.append(text[start:position])
            start = None
    return joined_lines


def create_subtitle(
    sub_maker: SubMaker,
    text: str,
    subtitle_file: str,
    word_level: bool = False,
):
    """
    优化字幕文件
    1. 将字幕文件按照标点符号分割成多行
    2. 逐行匹配字幕文件中的文本
    3. 生成新的字幕文件
    如果 word_level 为 True，直接输出逐词单条字幕。
    """
    text = _format_text(text)
    try:
        if word_level:
            if hasattr(sub_maker, "cues") and sub_maker.cues:
                sub_items = _build_subtitle_items_from_edge_cues_words(sub_maker)
            else:
                sub_items = _build_subtitle_items_from_legacy_submaker_words(sub_maker)
            if sub_items:
                _write_subtitle_items(sub_items, subtitle_file)
                return

        # 只有符号的行（如 `* * *`、`———`、`• • •` 场景分隔）不会被朗读，
        # 也不会得到任何词级时间轴；保留它们会让行数永远对不上，整段字幕
        # 都无法生成。
        script_lines = [
            line
            for line in utils.split_string_by_punctuations(text)
            if re.sub(r"[_\W]+", "", line)
        ]
        if hasattr(sub_maker, "cues") and sub_maker.cues:
            script_lines = _join_lines_split_inside_words(
                text, script_lines, [cue.content for cue in sub_maker.cues]
            )
            sub_items = _build_subtitle_items_from_edge_cues(sub_maker, script_lines)
        else:
            script_lines = _join_lines_split_inside_words(
                text, script_lines, getattr(sub_maker, "subs", [])
            )
            sub_items = _build_subtitle_items_from_legacy_submaker(
                sub_maker, script_lines
            )

        if len(sub_items) != len(script_lines):
            logger.warning(
                f"failed, sub_items len: {len(sub_items)}, script_lines len: {len(script_lines)}"
            )
            return

        _write_subtitle_items(sub_items, subtitle_file)
    except Exception as e:
        logger.error(f"failed, error: {str(e)}")


def _get_audio_duration_from_submaker(sub_maker: SubMaker):
    """
    获取音频时长
    """
    if hasattr(sub_maker, "duration") and getattr(sub_maker, "duration", 0) > 0:
        return float(getattr(sub_maker, "duration"))

    # Utamakan struktur `cues`; bila yang dipakai struktur lama hasil isian
    # manual (teks penuh), baca `offset`.
    if hasattr(sub_maker, "cues") and sub_maker.cues:
        return sub_maker.cues[-1].end.total_seconds()

    legacy_offsets = getattr(sub_maker, "offset", [])
    if not legacy_offsets:
        return 0.0
    return legacy_offsets[-1][1] / 10000000

def _get_audio_duration_from_file(audio_file: str) -> float:
    """
    获取音频文件时长（支持 mp3/m4a/wav/aac 等 ffmpeg 可解码的格式）
    """
    if not os.path.exists(audio_file):
        logger.error(f"audio file does not exist: {audio_file}")
        return 0.0

    try:
        # Use moviepy (ffmpeg) to read the duration of any supported audio format
        with AudioFileClip(audio_file) as audio:
            return audio.duration  # Duration in seconds
    except Exception as e:
        logger.error(f"Failed to get audio duration from file: {str(e)}")
        return 0.0

def get_audio_duration(target: Union[str, SubMaker]) -> float:
    """
    获取音频时长
    如果是SubMaker对象，则从SubMaker中获取时长
    如果是音频文件路径，则从音频文件中获取时长（支持 mp3/m4a/wav 等格式）
    """
    if isinstance(target, SubMaker):
        return _get_audio_duration_from_submaker(target)
    elif isinstance(target, str):
        return _get_audio_duration_from_file(target)
    else:
        logger.error(f"Invalid target type: {type(target)}")
        return 0.0
