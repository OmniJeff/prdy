import json
import anthropic
from config import ANTHROPIC_API_KEY
from prompts.system_prompts import PRD_ASSISTANT_PROMPT, PRD_GENERATION_PROMPT


PRODUCT_EXTRACTION_PROMPT = """Analyze the following content and extract the product information being discussed.

Return a JSON object with these fields:
- product_name: The name or type of product (e.g., "TaskFlow", "project management app", "CRM tool")
- product_description: A brief 1-2 sentence description of what the product does and who it's for
- search_category: A clean, search-friendly product category for competitive research. Remove marketing words (premium, deluxe, pro, ultimate, etc.) and brand names. Focus on the core product type with key differentiating features. Examples: "adjustable weight bench home gym", "project management software teams", "mobile budgeting app"
- confidence: "high" if the product is clearly defined, "medium" if somewhat clear, "low" if vague, "none" if no product info found

If there's not enough information to determine the product, return:
{"product_name": null, "product_description": null, "search_category": null, "confidence": "none"}

Return ONLY the JSON object, no other text."""


class APIError(Exception):
    """Custom exception for API errors with user-friendly messages."""
    pass


class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-20250514"

    def _handle_api_error(self, e: Exception) -> None:
        """Convert API errors to user-friendly messages."""
        error_message = str(e)

        if "credit balance is too low" in error_message:
            raise APIError(
                "API credit balance is too low. Please add credits at "
                "console.anthropic.com to continue using PRDy."
            )
        elif "invalid_api_key" in error_message or "authentication" in error_message.lower():
            raise APIError(
                "Invalid API key. Please check your ANTHROPIC_API_KEY in the .env file."
            )
        elif "rate_limit" in error_message:
            raise APIError(
                "Rate limit exceeded. Please wait a moment and try again."
            )
        elif "overloaded" in error_message:
            raise APIError(
                "The API is currently overloaded. Please try again in a few moments."
            )
        else:
            raise APIError(f"API error: {error_message}")

    def chat(self, messages: list[dict]) -> str:
        """Send a message and get a response, maintaining conversation history."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=PRD_ASSISTANT_PROMPT,
                messages=messages
            )
            return response.content[0].text
        except anthropic.APIError as e:
            self._handle_api_error(e)

    def generate_prd(self, messages: list[dict]) -> str:
        """Generate a final PRD document from the conversation."""
        generation_messages = messages + [
            {
                "role": "user",
                "content": PRD_GENERATION_PROMPT
            }
        ]

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=PRD_ASSISTANT_PROMPT,
                messages=generation_messages
            )
            return response.content[0].text
        except anthropic.APIError as e:
            self._handle_api_error(e)

    def extract_product_context(
        self, messages: list[dict] = None, prd_content: str = None
    ) -> dict:
        """
        Extract product name and description from conversation or PRD content.

        Args:
            messages: Conversation history (list of message dicts)
            prd_content: Raw PRD markdown content

        Returns:
            Dict with product_name, product_description, and confidence level
        """
        # Build content to analyze
        if prd_content:
            # Use first 4000 chars of PRD for extraction
            content_to_analyze = f"PRD Document:\n{prd_content[:4000]}"
        elif messages:
            # Build condensed conversation (last 10 messages, truncated)
            content_to_analyze = "Conversation:\n" + "\n".join([
                f"{m['role'].upper()}: {m['content'][:500]}"
                for m in messages[-10:]
            ])
        else:
            return {
                "product_name": None,
                "product_description": None,
                "confidence": "none"
            }

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                system="You are a product context extractor. Extract product information and return valid JSON only. Do not wrap in markdown code blocks.",
                messages=[{
                    "role": "user",
                    "content": f"{PRODUCT_EXTRACTION_PROMPT}\n\n{content_to_analyze}"
                }]
            )

            # Parse JSON response - strip markdown code blocks if present
            response_text = response.content[0].text.strip()

            # Remove markdown code fences if present
            if response_text.startswith("```"):
                # Remove opening fence (```json or ```)
                lines = response_text.split("\n")
                lines = lines[1:]  # Remove first line with ```
                # Find and remove closing fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            result = json.loads(response_text)
            return result
        except json.JSONDecodeError as e:
            return {
                "product_name": None,
                "product_description": None,
                "confidence": "none",
                "error": f"Failed to parse extraction response: {str(e)}"
            }
        except anthropic.APIError as e:
            return {
                "product_name": None,
                "product_description": None,
                "confidence": "none",
                "error": str(e)
            }
