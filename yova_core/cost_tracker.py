from yova_shared import get_clean_logger
from datetime import datetime
import json
from pathlib import Path

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
    def __init__(self, logger, usage_log_location=None, daily_budget=None):
        self.logger = get_clean_logger("cost_tracker", logger)
        self.cost = 0
        self.usage_log_location = usage_log_location
        self.usage_log = []
        self.daily_budget = daily_budget
        
        if usage_log_location:
            current_log_filepath = self.usage_log_location / self.get_current_log_filename()

            # read log if it exists
            if current_log_filepath.exists():
                with open(current_log_filepath, "r") as f:
                    self.usage_log = json.load(f)
                    self.cost = sum(log["cost"] for log in self.usage_log)
                    self.logger.info(f"Loaded {len(self.usage_log)} usage logs from {current_log_filepath}. Total cost: ${self.cost:.5f}")

    def is_budget_exceeded(self):
        if not self.daily_budget:
            return False
        return self.cost >= self.daily_budget

    def get_current_log_filename(self):
        return self.usage_log_location / f"usage_{datetime.now().strftime('%Y-%m-%d')}.json"

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

        self.usage_log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "model": model,
            "input_text_tokens": input_text_tokens,
            "input_audio_tokens": input_audio_tokens,
            "output_text_tokens": output_text_tokens,
            "output_audio_tokens": output_audio_tokens,
            "cost": cost,
        })
        self.save_usage_log()

    def save_usage_log(self):
        if not self.usage_log_location:
            return

        if not self.usage_log_location.exists():
            self.usage_log_location.mkdir(parents=True, exist_ok=True)

        current_log_filepath = self.usage_log_location / self.get_current_log_filename()
        with open(current_log_filepath, "w") as f:
            json.dump(self.usage_log, f, indent=2)

    def _get_cost(self, price_table, position, tokens):
        if position not in price_table:
            self.logger.warning(f"Model {price_table} does not have {position} in price table. skipping cost tracking for this segment.")
            return 0
        return price_table[position] * tokens / 1000000


