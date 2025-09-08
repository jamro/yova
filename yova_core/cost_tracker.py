from yova_shared import get_clean_logger


PRICE_TABLES = {
    "gpt-4o-mini-tts": { # price per 1M tokens
        "input_text_tokens": 0.60,
        "output_audio_tokens": 12.00
    },
    "gpt-4o-transcribe": { # price per 1M tokens
        "input_text_tokens": 6.00,
        "output_text_tokens": 10.00
    },
    "gpt-4o-mini-transcribe": { # price per 1M tokens
        "input_text_tokens": 3.00,
        "output_text_tokens": 5.00
    },
}

class CostTracker:
    def __init__(self, logger):
        self.logger = get_clean_logger("cost_tracker", logger)
        self.cost = 0

    def add_cost(self, model, input_text_tokens=0, input_audio_tokens=0, output_text_tokens=0, output_audio_tokens=0):
        self.logger.info(f"Tracking cost for model: {model}, input_text_tokens: {input_text_tokens}, input_audio_tokens: {input_audio_tokens}, output_text_tokens: {output_text_tokens}, output_audio_tokens: {output_audio_tokens}")

        if model not in PRICE_TABLES:
            self.logger.warning(f"Model {model} not found in price tables. skipping cost tracking for this operation.")
            return

        price_table = PRICE_TABLES[model]

        cost = 0
        cost += self._get_cost(price_table, "input_text_tokens", input_text_tokens)
        cost += self._get_cost(price_table, "input_audio_tokens", input_audio_tokens)
        cost += self._get_cost(price_table, "output_text_tokens", output_text_tokens)
        cost += self._get_cost(price_table, "output_audio_tokens", output_audio_tokens)
        self.cost += cost

        self.logger.info(f"Cost of operation: ${cost:.5f}. Total cost: ${self.cost:.5f}")

    def _get_cost(self, price_table, position, tokens):
        if position not in price_table:
            self.logger.warning(f"Model {price_table} does not have {position} in price table. skipping cost tracking for this segment.")
            return 0
        return price_table[position] * tokens / 1000000


