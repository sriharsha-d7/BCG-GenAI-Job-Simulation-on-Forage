"""``python -m fin_chatbot`` for an interactive session, or ``--ask "..."`` for one question."""

from __future__ import annotations

import argparse

from .engine import answer


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="fin_chatbot")
    ap.add_argument("--ask", help="answer one question and exit")
    ap.add_argument("--llm", action="store_true", help="use Claude to parse the question (needs ANTHROPIC_API_KEY)")
    a = ap.parse_args(argv)
    ask = answer
    if a.llm:
        from .llm import answer_with_llm as ask  # noqa: N813
    if a.ask:
        print(ask(a.ask).text)
        return
    print("Financial assistant (Apple, Microsoft, Tesla; FY2022-2024). Type 'quit' to exit.")
    while True:
        try:
            q = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"quit", "exit", "bye", "q"}:
            break
        if q:
            print("Bot:", ask(q).text)


if __name__ == "__main__":
    main()
