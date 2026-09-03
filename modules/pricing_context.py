from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


DEFAULT_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
}


@dataclass
class PricingContext:
    """Reusable token-based pricing calculator for hosted LLM calls.

    This is designed for illustrative pricing only. Local Ollama requests are not
    billed by the same formula, but this helper keeps the cost logic consistent
    across future calls.
    """

    model_prices: Dict[str, Dict[str, float]] = field(default_factory=lambda: DEFAULT_PRICING.copy())
    last_summary: Optional[Dict[str, float]] = field(default=None, init=False, repr=False)

    def __enter__(self) -> "PricingContext":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def __str__(self) -> str:
        if self.last_summary is None:
            return "PricingContext(model_prices={})".format(self.model_prices)

        return (
            "PricingContext(input_tokens={}, output_tokens={}, "
            "total_cost=${:.8f})"
        ).format(
            self.last_summary["input_tokens"],
            self.last_summary["output_tokens"],
            self.last_summary["total_cost"],
        )

    def get_rates(self, model_name: str) -> Dict[str, float]:
        return self.model_prices.get(model_name, {"input": 0.0, "output": 0.0})

    def estimate_usage(self, usage: Any, model_name: str) -> Dict[str, float]:
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)
        total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens)

        rates = self.get_rates(model_name)
        input_cost = (input_tokens / 1_000_000) * rates.get("input", 0.0)
        output_cost = (output_tokens / 1_000_000) * rates.get("output", 0.0)
        total_cost = input_cost + output_cost

        summary = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
        }
        self.last_summary = summary
        return summary

    def estimate_response(self, response: Any, model_name: Optional[str] = None) -> Dict[str, float]:
        target_model = model_name or getattr(response, "model", "unknown")
        return self.estimate_usage(response.usage, target_model)

    def run_and_price(
        self,
        client: Any,
        model: str,
        prompt: str,
        pricing_model: str = "gpt-4o",
        **kwargs: Any,
    ) -> tuple[Any, "PricingContext", Dict[str, float]]:
        with self as pricing:
            response = client.responses.create(model=model, input=prompt, **kwargs)
            summary = pricing.estimate_response(response, model_name=pricing_model)
            print(response.output_text)
            print(pricing)
            return response, pricing, summary

    def print_summary(self, response: Any, model_name: Optional[str] = None) -> Dict[str, float]:
        summary = self.estimate_response(response, model_name)
        print("Input tokens:", summary["input_tokens"])
        print("Output tokens:", summary["output_tokens"])
        print(f"Estimated cost: ${summary['total_cost']:.8f}")
        return summary
