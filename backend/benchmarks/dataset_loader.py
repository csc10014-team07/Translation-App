"""
Dataset Loader & Downloader for Translation App Benchmarking.

Handles fetching, caching, and serving:
1. FLORES-200 En-Vi translation pairs (academic MT gold standard)
2. FLEURS Vietnamese speech samples (ASR/TTS gold standard)
3. Context presets: curated cases plus online En-Vi corpora
"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
import tarfile
import unicodedata
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_BENCHMARK_DIR = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = DEFAULT_BENCHMARK_DIR / "cache"
CONTEXT_DATA_PATH = DEFAULT_BENCHMARK_DIR / "data" / "context_test_set.json"

MIN_EVAL_SAMPLES = 100
USER_AGENT = "TranslationAppBenchmark/1.0 (+https://github.com/anomalyco/opencode)"

FLORES_TAR_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
FLORES_LICENSE = "CC-BY-SA-4.0"
FLEURS_TSV_URL = "https://huggingface.co/datasets/google/fleurs/resolve/main/data/vi_vn/test.tsv"
FLEURS_AUDIO_TAR_URL = (
    "https://huggingface.co/datasets/google/fleurs/resolve/main/data/vi_vn/audio/test.tar.gz"
)
FLEURS_LICENSE = "CC-BY-4.0"
FLEURS_SAMPLE_RATE = 16000
TATOEBA_ZIP_URL = "https://object.pouta.csc.fi/OPUS-Tatoeba/v2021-07-22/moses/en-vi.txt.zip"
TATOEBA_LICENSE = "CC-BY-2.0"
QED_ZIP_URL = "https://object.pouta.csc.fi/OPUS-QED/v2.0a/moses/en-vi.txt.zip"
QED_LICENSE = "research-only"

CONTEXT_PRESET_TARGETS = {
    "Formal": 20,
    "Friendly": 20,
    "IT": 20,
    "Medical": 15,
    "Travel": 15,
    "General": 10,
}

CONTEXT_PRESET_RULES = {
    "Formal": {
        "required": [
            "quý khách",
            "quý vị",
            "vui lòng",
            "trân trọng",
            "anh/chị",
        ],
        "forbidden": ["mày", "tao", "cậu", "nhé", "nha", "oke"],
        "sources": ["Tatoeba", "FLORES-200"],
    },
    "Friendly": {
        "required": ["bạn", "mình", "cậu", "nhé", "nha", "cảm ơn", "vui"],
        "forbidden": ["quý khách", "quý vị", "kính"],
        "sources": ["Tatoeba"],
    },
    "IT": {
        "required": [
            "máy tính",
            "phần mềm",
            "dữ liệu",
            "lập trình",
            "mã",
            "hệ thống",
            "internet",
            "công nghệ",
            "điện thoại",
            "ứng dụng",
        ],
        "forbidden": [],
        "sources": ["QED", "FLORES-200"],
    },
    "Medical": {
        "required": [
            "bệnh",
            "sức khỏe",
            "bác sĩ",
            "thuốc",
            "điều trị",
            "y tế",
            "bệnh nhân",
            "ung thư",
            "nhiễm",
            "virus",
        ],
        "forbidden": [],
        "sources": ["FLORES-200", "QED"],
    },
    "Travel": {
        "required": [
            "du lịch",
            "khách sạn",
            "sân bay",
            "chuyến bay",
            "vé",
            "đặt phòng",
            "hành lý",
            "nhà ga",
            "bến tàu",
            "tham quan",
        ],
        "forbidden": [],
        "sources": ["Tatoeba", "FLORES-200"],
    },
    "General": {
        "required": [],
        "forbidden": [],
        "sources": ["FLORES-200", "Tatoeba"],
    },
}

VIETNAMESE_STOPWORDS = {
    "anh",
    "bao",
    "bạn",
    "bằng",
    "bị",
    "các",
    "cái",
    "cần",
    "cho",
    "chúng",
    "có",
    "cô",
    "cũng",
    "của",
    "đã",
    "đang",
    "để",
    "đến",
    "đi",
    "đó",
    "được",
    "em",
    "gì",
    "hai",
    "hay",
    "họ",
    "khi",
    "không",
    "là",
    "lại",
    "lên",
    "mà",
    "một",
    "này",
    "nên",
    "nếu",
    "người",
    "như",
    "những",
    "ở",
    "ông",
    "ra",
    "rồi",
    "sẽ",
    "sự",
    "tại",
    "thì",
    "trong",
    "từ",
    "và",
    "về",
    "vì",
    "với",
}

# First 10 pairs of FLORES-200 devtest (eng_Latn-vie_Latn), copied verbatim
# from the official tarball at FLORES_TAR_URL. License: CC-BY-SA-4.0.
# This is only an offline fallback: 10 pairs do not satisfy MIN_EVAL_SAMPLES,
# so it must never be presented as a full FLORES-200 benchmark result.
BUILTIN_FLORES_PAIRS = [
    {
        "source": "\"We now have 4-month-old mice that are non-diabetic that used to be diabetic,\" he added.",
        "reference": "“Chúng tôi hiện có đàn chuột 4 tháng tuổi đã hết bị tiểu đường,” ông nói thêm.",
    },
    {
        "source": "Dr. Ehud Ur, professor of medicine at Dalhousie University in Halifax, Nova Scotia and chair of the clinical and scientific division of the Canadian Diabetes Association cautioned that the research is still in its early days.",
        "reference": "Tiến sĩ Ehud Ur, giáo sư y khoa của Trường Đại học Dalhousie ở Halifax, Nova Scotia và là chủ tịch ban lâm sàng và khoa học của Hiệp hội Bệnh Tiểu đường Canada cảnh báo rằng nghiên cứu này chỉ mới là sự khởi đầu.",
    },
    {
        "source": "Like some other experts, he is skeptical about whether diabetes can be cured, noting that these findings have no relevance to people who already have Type 1 diabetes.",
        "reference": "Giống như một số chuyên gia khác, ông ấy hoài nghi về khả năng chữa bệnh tiểu đường, với lưu ý rằng các phát hiện này không liên quan tới người đã bị tiểu đường tuýp 1.",
    },
    {
        "source": "On Monday, Sara Danius, permanent secretary of the Nobel Committee for Literature at the Swedish Academy, publicly announced during a radio program on Sveriges Radio in Sweden the committee, unable to reach Bob Dylan directly about winning the 2016 Nobel Prize in Literature, had abandoned its efforts to reach him.",
        "reference": "Vào ngày thứ Hai, Sara Danius, thư ký thường trực của Ủy Ban Nobel Văn Học thuộc Viện Hàn Lâm Thụy Điển, trong một chương trình phát thanh của Đài Phát Thanh Sveriges ở Thụy Điển, đã công bố rằng, vì không thể liên lạc trực tiếp với Bob Dylan về việc trao Giải Nobel Văn Học năm 2016, ủy ban đã ngừng nỗ lực liên lạc với ông.",
    },
    {
        "source": "Danius said, \"Right now we are doing nothing. I have called and sent emails to his closest collaborator and received very friendly replies. For now, that is certainly enough.\"",
        "reference": "Danius đã nói, “Ngay lúc này chúng ta chẳng làm gì cả. Tôi đã gọi và gửi email cho đối tác thân cận nhất của anh ta và nhận được phản hồi rất thân thiện. Hiện tại, như vậy là đủ.”",
    },
    {
        "source": "Previously, Ring's CEO, Jamie Siminoff, remarked the company started when his doorbell wasn't audible from his shop in his garage.",
        "reference": "Trước đây, giám đốc điều hành của Ring, Jamie Siminoff, đã phát biểu rằng công ty ra đời khi ông không nghe tiếng chuông cửa khi đang khi ở trong gara.",
    },
    {
        "source": "He built a WiFi door bell, he said.",
        "reference": "Ông đã lắp môt chuông cửa WiFi, ông cho biết.",
    },
    {
        "source": "Siminoff said sales boosted after his 2013 appearance in a Shark Tank episode where the show panel declined funding the startup.",
        "reference": "Siminoff cho biết doanh số tăng sau sự xuất hiện của mình vào năm 2013 trong một tập Shark Tank khi hội đồng giám khảo chương trình đã từ chối tài trợ cho công ty khởi nghiệp.",
    },
    {
        "source": "In late 2017, Siminoff appeared on shopping television channel QVC.",
        "reference": "Vào cuối năm 2017, Siminoff xuất hiện trên kênh truyền hình mua sắm QVC.",
    },
    {
        "source": "Ring also settled a lawsuit with competing security company, the ADT Corporation.",
        "reference": "Ring cũng đã dàn xếp một vụ kiện với một công ty an ninh đối thủ là ADT Corporation.",
    },
]


def load_context_dataset() -> list[dict[str, Any]]:
    """Load curated context presets evaluation dataset."""
    if not CONTEXT_DATA_PATH.exists():
        logger.warning("Context test dataset not found at %s", CONTEXT_DATA_PATH)
        return []
    with open(CONTEXT_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _download_bytes(url: str, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _contains_keyword(text: str, keyword: str) -> bool:
    needle = unicodedata.normalize("NFC", keyword)
    pattern = r"(?<!\w)" + re.escape(needle) + r"(?!\w)"
    return re.search(pattern, unicodedata.normalize("NFC", text), flags=re.IGNORECASE) is not None


def _extract_tar_member(tf: tarfile.TarFile, suffix: str) -> str:
    for member in tf.getmembers():
        if member.isfile() and member.name.endswith(suffix):
            extracted = tf.extractfile(member)
            if extracted is not None:
                return extracted.read().decode("utf-8")
    raise KeyError(f"Missing tar member ending with {suffix!r}")


def _extract_zip_pairs(data: bytes, prefix: str) -> list[tuple[str, str]]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        en_name = next((n for n in names if n.endswith(f"{prefix}.en-vi.en")), None)
        vi_name = next((n for n in names if n.endswith(f"{prefix}.en-vi.vi")), None)
        if en_name is None or vi_name is None:
            raise KeyError(f"Expected {prefix}.en-vi.en/.vi in {names[:5]}")
        en_lines = archive.read(en_name).decode("utf-8").splitlines()
        vi_lines = archive.read(vi_name).decode("utf-8").splitlines()
    return [
        (en.strip(), vi.strip())
        for en, vi in zip(en_lines, vi_lines, strict=False)
        if en.strip() and vi.strip()
    ]


def get_flores_dataset(
    limit: int = MIN_EVAL_SAMPLES,
    cache_dir: Path | None = None,
    allow_download: bool = True,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """
    Load FLORES-200 English -> Vietnamese translation pairs with provenance.

    Returns ``(pairs, metadata)`` where metadata records whether the pairs came
    from the local cache, a fresh download, or the small built-in fallback set.
    """
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "flores200_en_vi.json"
    metadata: dict[str, Any] = {
        "source": "builtin",
        "cache_file": str(cache_file),
        "requested_limit": limit,
        "minimum_required": MIN_EVAL_SAMPLES,
        "dataset": "FLORES-200 devtest eng_Latn-vie_Latn",
        "license": FLORES_LICENSE,
        "url": FLORES_TAR_URL,
    }

    # 1. Check local cache
    if cache_file.exists():
        try:
            cached_data = _read_json(cache_file)
            if cached_data and isinstance(cached_data, list):
                pairs = cached_data[:limit]
                metadata.update(
                    {
                        "source": "cache",
                        "returned_pairs": len(pairs),
                        "available_pairs": len(cached_data),
                        "meets_requirement": len(pairs) >= MIN_EVAL_SAMPLES,
                    }
                )
                return pairs, metadata
        except Exception as e:
            logger.debug("Failed reading cache %s: %s", cache_file, e)

    # 2. Try downloading the official FLORES-200 tarball.
    if allow_download:
        try:
            payload = _download_bytes(FLORES_TAR_URL)
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tf:
                en_text = _extract_tar_member(tf, "eng_Latn.devtest")
                vi_text = _extract_tar_member(tf, "vie_Latn.devtest")
            en_lines = en_text.strip().splitlines()
            vi_lines = vi_text.strip().splitlines()
            pairs = [
                {"source": en.strip(), "reference": vi.strip()}
                for en, vi in zip(en_lines, vi_lines, strict=False)
                if en.strip() and vi.strip()
            ]
            if pairs:
                _write_json(cache_file, pairs)
                logger.info("Cached %d FLORES-200 pairs to %s", len(pairs), cache_file)
                result = pairs[:limit]
                metadata.update(
                    {
                        "source": "download",
                        "returned_pairs": len(result),
                        "available_pairs": len(pairs),
                        "meets_requirement": len(result) >= MIN_EVAL_SAMPLES,
                    }
                )
                return result, metadata
        except Exception as exc:
            logger.debug("Online FLORES download skipped/failed (%s), using built-in gold set", exc)

    # 3. Fallback to the verified first 10 FLORES-200 devtest pairs
    pairs = BUILTIN_FLORES_PAIRS[:limit]
    metadata.update(
        {
            "source": "builtin",
            "dataset": "FLORES-200 devtest eng_Latn-vie_Latn (10-pair fallback)",
            "returned_pairs": len(pairs),
            "available_pairs": len(BUILTIN_FLORES_PAIRS),
            "meets_requirement": len(pairs) >= MIN_EVAL_SAMPLES,
        }
    )
    return pairs, metadata


def get_flores_samples(
    limit: int = MIN_EVAL_SAMPLES,
    cache_dir: Path | None = None,
    allow_download: bool = True,
) -> list[dict[str, str]]:
    """Backward-compatible wrapper around :func:`get_flores_dataset`."""
    return get_flores_dataset(
        limit=limit,
        cache_dir=cache_dir,
        allow_download=allow_download,
    )[0]


def _parse_fleurs_tsv(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    for raw_row in reader:
        if len(raw_row) < 7:
            continue
        row_id, filename, transcription, raw_transcription, _phonemes, num_samples, gender = raw_row[:7]
        filename = filename.strip()
        transcription = transcription.strip()
        if not filename or not transcription:
            continue
        try:
            duration_s = int(num_samples) / FLEURS_SAMPLE_RATE
        except ValueError:
            duration_s = 0.0
        rows.append(
            {
                "id": row_id.strip() or Path(filename).stem,
                "filename": filename,
                "text": transcription,
                "raw_text": raw_transcription.strip(),
                "duration_s": duration_s,
                "gender": gender.strip(),
            }
        )
    return rows


def get_fleurs_test_rows(
    limit: int | None = None,
    cache_dir: Path | None = None,
    allow_download: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load FLEURS vi_vn test metadata from cache or Hugging Face."""
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "fleurs_vi_vn_test.json"
    metadata: dict[str, Any] = {
        "source": "missing",
        "cache_file": str(cache_file),
        "requested_limit": limit,
        "minimum_required": MIN_EVAL_SAMPLES,
        "dataset": "google/fleurs vi_vn test",
        "license": FLEURS_LICENSE,
        "url": FLEURS_TSV_URL,
    }

    rows: list[dict[str, Any]] = []
    if cache_file.exists():
        try:
            cached = _read_json(cache_file)
            if cached and isinstance(cached, list):
                rows = cached
                metadata["source"] = "cache"
        except Exception as e:
            logger.debug("Failed reading cache %s: %s", cache_file, e)

    if not rows and allow_download:
        try:
            text = _download_bytes(FLEURS_TSV_URL).decode("utf-8")
            rows = _parse_fleurs_tsv(text)
            if rows:
                _write_json(cache_file, rows)
                metadata["source"] = "download"
                logger.info("Cached %d FLEURS test rows to %s", len(rows), cache_file)
        except Exception as exc:
            logger.warning("FLEURS metadata download failed: %s", exc)
            metadata["error"] = str(exc)

    selected = rows[:limit] if limit is not None else rows
    metadata.update(
        {
            "returned_rows": len(selected),
            "available_rows": len(rows),
            "meets_requirement": len(selected) >= MIN_EVAL_SAMPLES,
        }
    )
    return selected, metadata


def get_fleurs_asr_dataset(
    limit: int = MIN_EVAL_SAMPLES,
    cache_dir: Path | None = None,
    allow_download: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Build a FLEURS ASR test set with verified references.

    The 544MB audio tarball is streamed and reading stops after ``limit`` files,
    so a 100-sample run only downloads the first matching audio members.
    """
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    dataset_dir = cache_dir / "fleurs_vi_vn_asr"
    audio_dir = dataset_dir / "audio"
    metadata_file = dataset_dir / "metadata.json"
    audio_dir.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "source": "missing",
        "cache_dir": str(dataset_dir),
        "requested_limit": limit,
        "minimum_required": MIN_EVAL_SAMPLES,
        "dataset": "google/fleurs vi_vn test",
        "license": FLEURS_LICENSE,
        "url": FLEURS_AUDIO_TAR_URL,
        "reference_verified": True,
    }

    samples: list[dict[str, Any]] = []
    if metadata_file.exists():
        try:
            cached = _read_json(metadata_file)
            if cached and isinstance(cached, list):
                samples = cached
                metadata["source"] = "cache"
        except Exception as e:
            logger.debug("Failed reading cache %s: %s", metadata_file, e)

    if len(samples) < limit and allow_download:
        rows, rows_meta = get_fleurs_test_rows(limit=None, cache_dir=cache_dir, allow_download=True)
        metadata["metadata_source"] = rows_meta.get("source")
        by_filename = {
            row["filename"]: row for row in rows if row.get("filename") and row["duration_s"] <= 30.0
        }
        existing = {Path(sample["audio_path"]).name for sample in samples}
        needed = limit - len(samples)
        downloaded = 0

        if by_filename and needed > 0:
            try:
                request = urllib.request.Request(FLEURS_AUDIO_TAR_URL, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=120) as response:
                    with tarfile.open(fileobj=response, mode="r|gz") as tf:
                        for member in tf:
                            if not member.isfile():
                                continue
                            name = Path(member.name).name
                            if name in existing or name not in by_filename:
                                continue
                            extracted = tf.extractfile(member)
                            if extracted is None:
                                continue
                            payload = extracted.read()
                            if len(payload) < 100:
                                continue
                            audio_path = audio_dir / name
                            audio_path.write_bytes(payload)
                            row = by_filename[name]
                            samples.append(
                                {
                                    "id": Path(name).stem,
                                    "audio_path": str(audio_path.resolve()),
                                    "reference": row["text"],
                                    "reference_verified": True,
                                    "duration_s": round(row["duration_s"], 3),
                                    "source": "google/fleurs",
                                    "license": FLEURS_LICENSE,
                                }
                            )
                            existing.add(name)
                            downloaded += 1
                            if len(samples) >= limit:
                                break
                metadata["source"] = "cache+download" if downloaded else metadata["source"]
                logger.info("Cached %d FLEURS ASR samples to %s", len(samples), dataset_dir)
            except Exception as exc:
                logger.warning("FLEURS audio streaming failed: %s", exc)
                metadata["error"] = str(exc)
                if downloaded:
                    metadata["source"] = "partial-download"

        if samples:
            _write_json(metadata_file, samples)

    if not samples:
        fallback = get_asr_samples(limit=limit)
        metadata.update(
            {
                "source": "local_fallback",
                "returned_samples": len(fallback),
                "available_samples": len(fallback),
                "meets_requirement": False,
                "reference_verified": False,
            }
        )
        return fallback, metadata

    selected = samples[:limit]
    metadata.update(
        {
            "returned_samples": len(selected),
            "available_samples": len(samples),
            "meets_requirement": len(selected) >= MIN_EVAL_SAMPLES,
        }
    )
    return selected, metadata


def get_tts_samples(
    limit: int = MIN_EVAL_SAMPLES,
    cache_dir: Path | None = None,
    allow_download: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select Vietnamese sentences from FLEURS for TTS synthesis."""
    if limit <= 0:
        return [], {
            "source": "disabled",
            "dataset": "google/fleurs vi_vn test",
            "license": FLEURS_LICENSE,
            "url": FLEURS_TSV_URL,
            "requested_limit": limit,
            "returned_samples": 0,
            "available_rows": 0,
            "minimum_required": MIN_EVAL_SAMPLES,
            "meets_requirement": False,
        }
    rows, rows_meta = get_fleurs_test_rows(limit=None, cache_dir=cache_dir, allow_download=allow_download)
    samples: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    for row in rows:
        text = row.get("text", "").strip()
        word_count = len(text.split())
        if not text or word_count < 3 or word_count > 25:
            continue
        if row.get("duration_s", 0.0) > 30.0:
            continue
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        if normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        samples.append(
            {
                "id": Path(row["filename"]).stem,
                "text": text,
                "language": "vi",
                "source": "google/fleurs",
                "license": FLEURS_LICENSE,
                "reference_duration_s": round(row.get("duration_s", 0.0), 3),
            }
        )
        if len(samples) >= limit:
            break

    metadata = {
        "source": rows_meta.get("source", "missing"),
        "dataset": "google/fleurs vi_vn test",
        "license": FLEURS_LICENSE,
        "url": FLEURS_TSV_URL,
        "requested_limit": limit,
        "returned_samples": len(samples),
        "available_rows": rows_meta.get("available_rows", 0),
        "minimum_required": MIN_EVAL_SAMPLES,
        "meets_requirement": len(samples) >= MIN_EVAL_SAMPLES,
    }
    if rows_meta.get("error"):
        metadata["error"] = rows_meta["error"]
    return samples, metadata


def _context_keywords(reference: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", reference).lower()
    words = [
        word
        for word in re.findall(r"\w+", normalized)
        if len(word) >= 3 and not word.isdigit() and word not in VIETNAMESE_STOPWORDS
    ]
    unique = sorted(set(words), key=lambda word: (-len(word), word))
    return unique[:3]


def _build_context_sample(
    preset: str,
    source_text: str,
    reference: str,
    source_name: str,
    source_url: str,
    license_name: str,
    index: int,
) -> dict[str, Any] | None:
    rules = CONTEXT_PRESET_RULES[preset]
    if not (4 <= len(reference.split()) <= 60):
        return None
    if preset == "General":
        required = _context_keywords(reference)
        if len(required) < 2:
            return None
    else:
        required = [cue for cue in rules["required"] if _contains_keyword(reference, cue)][:4]
        if not required:
            return None
    return {
        "id": f"ctx_online_{preset.lower()}_{index:03d}",
        "preset": preset,
        "source_lang": "en",
        "target_lang": "vi",
        "source": source_text,
        "reference": reference,
        "required_keywords": required,
        "forbidden_keywords": rules["forbidden"],
        "source_dataset": source_name,
        "license": license_name,
        "source_url": source_url,
    }


def _load_online_context_pairs(cache_dir: Path) -> dict[str, list[tuple[str, str]]]:
    pairs: dict[str, list[tuple[str, str]]] = {}
    sources = [
        ("Tatoeba", TATOEBA_ZIP_URL, "Tatoeba"),
        ("QED", QED_ZIP_URL, "QED"),
    ]
    for source_name, url, prefix in sources:
        try:
            payload = _download_bytes(url)
            pairs[source_name] = _extract_zip_pairs(payload, prefix)
            logger.info("Loaded %d %s pairs", len(pairs[source_name]), source_name)
        except Exception as exc:
            logger.warning("Context source %s failed: %s", source_name, exc)
            pairs[source_name] = []

    try:
        flores_pairs, _ = get_flores_dataset(limit=2000, cache_dir=cache_dir, allow_download=True)
        pairs["FLORES-200"] = [(pair["source"], pair["reference"]) for pair in flores_pairs]
    except Exception as exc:
        logger.warning("Context source FLORES-200 failed: %s", exc)
        pairs["FLORES-200"] = []
    return pairs


def _select_online_context(
    pairs_by_source: dict[str, list[tuple[str, str]]],
    curated: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    curated_counts = {
        preset: sum(1 for item in curated if item.get("preset") == preset)
        for preset in CONTEXT_PRESET_TARGETS
    }
    needed = {
        preset: max(0, target - curated_counts.get(preset, 0))
        for preset, target in CONTEXT_PRESET_TARGETS.items()
    }

    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for preset, want in needed.items():
        if want <= 0:
            continue
        index = 0
        for source_name in CONTEXT_PRESET_RULES[preset]["sources"]:
            for source_text, reference in pairs_by_source.get(source_name, []):
                key = (source_text, reference)
                if key in seen:
                    continue
                sample = _build_context_sample(
                    preset=preset,
                    source_text=source_text,
                    reference=reference,
                    source_name=source_name,
                    source_url={
                        "Tatoeba": TATOEBA_ZIP_URL,
                        "QED": QED_ZIP_URL,
                        "FLORES-200": FLORES_TAR_URL,
                    }.get(source_name, ""),
                    license_name={
                        "Tatoeba": TATOEBA_LICENSE,
                        "QED": QED_LICENSE,
                        "FLORES-200": FLORES_LICENSE,
                    }.get(source_name, ""),
                    index=index,
                )
                if sample is None:
                    continue
                selected.append(sample)
                seen.add(key)
                index += 1
                if index >= want:
                    break
            if index >= want:
                break
    return selected


def get_context_dataset(
    limit: int = MIN_EVAL_SAMPLES,
    cache_dir: Path | None = None,
    allow_download: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Load at least 100 context cases: 15 curated cases plus online En-Vi pairs.

    Online samples are selected by preset-specific keyword cues. The merged
    selection is cached in ``context_online.json`` for deterministic reruns.
    """
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "context_online.json"
    curated = load_context_dataset()
    metadata: dict[str, Any] = {
        "source": "curated",
        "cache_file": str(cache_file),
        "requested_limit": limit,
        "minimum_required": MIN_EVAL_SAMPLES,
        "dataset": "curated + Tatoeba/QED/FLORES-200",
        "license": f"mixed: curated, {TATOEBA_LICENSE}, {QED_LICENSE}, {FLORES_LICENSE}",
        "licenses": ["curated", TATOEBA_LICENSE, QED_LICENSE, FLORES_LICENSE],
    }

    if not allow_download:
        samples = curated[:limit]
        metadata.update(
            {
                "returned_samples": len(samples),
                "available_samples": len(curated),
                "meets_requirement": len(samples) >= MIN_EVAL_SAMPLES,
            }
        )
        return samples, metadata

    online: list[dict[str, Any]] = []
    if cache_file.exists():
        try:
            cached = _read_json(cache_file)
            if cached and isinstance(cached, list):
                online = cached
                metadata["source"] = "cache"
        except Exception as e:
            logger.debug("Failed reading cache %s: %s", cache_file, e)

    if not online:
        pairs_by_source = _load_online_context_pairs(cache_dir)
        online = _select_online_context(pairs_by_source, curated)
        if online:
            _write_json(cache_file, online)
            metadata["source"] = "curated+online"
            logger.info("Cached %d online context samples to %s", len(online), cache_file)

    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in [*curated, *online]:
        key = (str(item.get("source", "")), str(item.get("reference", "")))
        if key in seen:
            continue
        merged.append(item)
        seen.add(key)

    samples = merged[:limit]
    preset_counts = {
        preset: sum(1 for item in samples if item.get("preset") == preset)
        for preset in CONTEXT_PRESET_TARGETS
    }
    metadata.update(
        {
            "returned_samples": len(samples),
            "available_samples": len(merged),
            "curated_samples": len(curated),
            "online_samples": len(online),
            "preset_counts": preset_counts,
            "meets_requirement": len(samples) >= MIN_EVAL_SAMPLES,
        }
    )
    return samples, metadata


LOCAL_ASR_SAMPLES = [
    ("sample_16k.wav", "Một hai ba bốn một hai ba bốn thử giọng thử giọng."),
    ("sample.wav", "Một hai ba bốn một hai ba bốn thử giọng thử giọng."),
    ("two.wav", "Một hai ba bốn một hai ba bốn thử giọng thử giọng."),
]


def get_asr_samples(
    limit: int = 10,
    workspace_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Load local repository WAV files for ASR smoke evaluation.

    VIVOS is not downloaded or bundled here. The references below are manual
    and marked as unverified, so WER/CER are only indicative until a human has
    checked them against the audio.
    """
    samples: list[dict[str, Any]] = []

    if workspace_root is None:
        workspace_root = DEFAULT_BENCHMARK_DIR.parent.parent

    for filename, approx_ref in LOCAL_ASR_SAMPLES:
        file_path = workspace_root / filename
        if file_path.exists() and file_path.stat().st_size > 1000:
            samples.append(
                {
                    "id": file_path.stem,
                    "audio_path": str(file_path.resolve()),
                    "reference": approx_ref,
                    "reference_verified": False,
                }
            )

    return samples[:limit]


def get_vivos_samples(
    limit: int = 10,
    workspace_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Deprecated alias for :func:`get_asr_samples`."""
    return get_asr_samples(limit=limit, workspace_root=workspace_root)
