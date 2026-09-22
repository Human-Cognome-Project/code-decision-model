"""Smoke-test the real UniXcoder adapter.

Install first:
    pip install -e ".[hf]"

This downloads microsoft/unixcoder-base on first run.
"""
import torch

from cdm import CodeDecisionModel
from cdm.unixcoder import UniXcoderEncoder


def main() -> None:
    encoder = UniXcoderEncoder(frozen=True)
    model = CodeDecisionModel(
        encoder=encoder,
        dim=encoder.dim,
        hidden=256,
    )

    context = """
def parse_packet(data):
    header = parse_header(data)
    return decode_payload(data, header)
"""
    question = "Which candidate is directly responsible for parsing the header?"
    candidates = [
        "parse_header(data): parse protocol header fields",
        "decode_payload(data, header): decode packet payload",
        "dispatch(packet): route a decoded packet",
    ]

    with torch.no_grad():
        p = model.probabilities(context, question, candidates)

    for candidate, probability in zip(candidates, p.tolist()):
        print(f"{probability:0.4f}  {candidate}")

    print()
    print("These probabilities are from an untrained decision head.")
    print("This script validates integration only; it is not a capability benchmark.")


if __name__ == "__main__":
    main()
