from app.services.text_normalizer import TextNormalizer


normalizer = TextNormalizer()


segments = [
    {
        "start": 1.56,
        "end": 9.72,
        "text": (
            "안녕하세요 음 저는 "
            "저는숭실대학교 학생입니다 "
            "그리고 컴퓨터학과입니다."
        ),
        "timestamps": [
            {
                "start": 1.56,
                "end": 1.62,
            },
            {
                "start": 1.74,
                "end": 1.80,
            },
            {
                "start": 2.10,
                "end": 2.16,
            },
            {
                "start": 2.46,
                "end": 2.52,
            },
            {
                "start": 2.76,
                "end": 2.82,
            },
            {
                "start": 3.06,
                "end": 3.12,
            },
            {
                "start": 3.30,
                "end": 3.36,
            },
            {
                "start": 3.54,
                "end": 3.60,
            },
            {
                "start": 3.84,
                "end": 3.90,
            },
            {
                "start": 4.32,
                "end": 4.38,
            },
            {
                "start": 5.46,
                "end": 5.52,
            },
            {
                "start": 5.88,
                "end": 5.94,
            },
            {
                "start": 6.06,
                "end": 6.12,
            },
            {
                "start": 6.30,
                "end": 6.36,
            },
            {
                "start": 6.84,
                "end": 6.90,
            },
        ],
    }
]


result = normalizer.normalize_segment(
    segments[0]
)


print()
print("===== NORMALIZED WORDS =====")

for word in result:

    print(
        f'{word["text"]}'
        f' | '
        f'{word.get("start")}'
        f' ~ '
        f'{word.get("end")}'
        f' | '
        f'{word["morphemes"]}'
    )