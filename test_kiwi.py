from kiwipiepy import Kiwi


kiwi = Kiwi()

texts = [
    "안녕하세요 음 저는 저는숭실대학교 학생입니다 그리고 컴퓨터학과입니다.",
    "음 저는 저는 숭실대학교 학생입니다.",
    "음악 음악",
    "저는 저는",
]


for text in texts:

    print()
    print("=" * 50)
    print("원문:")
    print(text)

    print()
    print("Kiwi 분석:")

    tokens = kiwi.tokenize(text)

    for token in tokens:

        print(
            f"{token.form:15}"
            f"{token.tag:8}"
            f"start={token.start:3}"
            f"len={token.len:3}"
        )