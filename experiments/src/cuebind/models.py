"""Model conditions F1, F2 and F4 (report, Section 3.3). Revisions are pinned for reproducibility."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from PIL import Image

LLM_ID, LLM_REV = "Qwen/Qwen2.5-3B-Instruct", "aa8e72537993ba99e69dfaafa59ed015b17504d1"
VLM_ID, VLM_REV = "Qwen/Qwen2.5-VL-3B-Instruct", "66285546d2b821cf421d4f5eb2576359d3770cd3"
VLM_MIN_PIXELS, VLM_MAX_PIXELS = 256 * 28 * 28, 1280 * 28 * 28

QUESTIONS = {
    "P1": "Care este data scadenței de pe această factură?",
    "P2": "Până la ce dată trebuie plătită această factură?",
}
ANSWER_ONLY = 'Answer with JSON only, in the form {"answer": "<value exactly as written>"}.'
ANSWER_AND_BOX = (
    'Answer with JSON only, in the form {"answer": "<value exactly as written>", '
    '"bbox_2d": [x1, y1, x2, y2]}, where bbox_2d is the box of the value in the image.'
)
F1_CONTEXT = "Textul extras din factură, rând cu rând:"
F2_CONTEXT = ("Textul extras din factură, rând cu rând. Fiecare cuvânt este urmat de caseta sa "
              "[x0,y0,x1,y1] pe pagină, pe o scară 0-1000:")


@dataclass(frozen=True)
class Generation:
    raw_output: str
    input_tokens: int
    seconds: float
    resized_image: tuple[int, int] | None = None


class TextModel:
    """F1 and F2 share this language model; only the serialization of the words differs."""

    def __init__(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(LLM_ID, revision=LLM_REV)
        self.model = AutoModelForCausalLM.from_pretrained(LLM_ID, revision=LLM_REV, dtype=torch.float32).eval()

    def prompt(self, context_header: str, document_text: str, question: str) -> str:
        return f"{context_header}\n{document_text}\n\n{question}\n{ANSWER_ONLY}"

    def generate(self, prompt: str) -> Generation:
        import time

        inputs = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], add_generation_prompt=True, return_tensors="pt", return_dict=True
        )
        start = time.perf_counter()
        with torch.inference_mode():
            out = self.model.generate(**inputs, max_new_tokens=48, do_sample=False)
        seconds = time.perf_counter() - start
        text = self.tokenizer.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return Generation(text, int(inputs["input_ids"].shape[1]), round(seconds, 2))


class VisionModel:
    """F4: the rendered image and the question; returns an answer and a box in resized-image pixels."""

    def __init__(self) -> None:
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.processor = AutoProcessor.from_pretrained(
            VLM_ID, revision=VLM_REV, size={"shortest_edge": VLM_MIN_PIXELS, "longest_edge": VLM_MAX_PIXELS}
        )
        self.model = AutoModelForImageTextToText.from_pretrained(VLM_ID, revision=VLM_REV, dtype=torch.float32).eval()

    def generate(self, image_path: str, question: str) -> Generation:
        import time

        image = Image.open(image_path).convert("RGB")
        messages = [{"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": f"{question}\n{ANSWER_AND_BOX}"},
        ]}]
        inputs = self.processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt"
        )
        _, grid_h, grid_w = inputs["image_grid_thw"][0].tolist()
        patch = self.processor.image_processor.patch_size
        start = time.perf_counter()
        with torch.inference_mode():
            out = self.model.generate(**inputs, max_new_tokens=64, do_sample=False)
        seconds = time.perf_counter() - start
        text = self.processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]
        return Generation(text, int(inputs["input_ids"].shape[1]), round(seconds, 2), (grid_w * patch, grid_h * patch))
