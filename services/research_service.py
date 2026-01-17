"""Research service using Perplexity AI for competitive intelligence."""
import requests
from config import PERPLEXITY_API_KEY


class ResearchService:
    """Service for conducting AI-powered web research on products and markets."""

    def __init__(self):
        self.api_key = PERPLEXITY_API_KEY
        self.api_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar"

    def research_competitors(self, product_name: str, product_description: str) -> str:
        """
        Research competitors using Perplexity AI.

        Args:
            product_name: Name/category of the product
            product_description: Brief description of the product

        Returns:
            Formatted competitive analysis from Perplexity
        """
        prompt = f"""Research the competitive landscape for: {product_name}

Product description: {product_description}

Provide a comprehensive competitive analysis with these sections:

## 1. Key Competitors
For each major competitor, include:
- **Company/Product Name**
- **Product URL** (actual links to product pages)
- **Price** (in USD)
- **Key Features** (2-3 bullet points)

## 2. Pricing Landscape
- Price ranges by tier (budget, mid-range, premium)
- Where {product_name} could be positioned

## 3. Feature Comparison
- Standard features across competitors
- Premium features that command higher prices

## 4. Market Gaps & Opportunities
- What's missing in current offerings
- Underserved customer segments

## 5. Strategic Recommendations
- Differentiation opportunities
- Recommended price point with justification

IMPORTANT:
- Focus on products available in the US market
- Include actual URLs as markdown links
- Include real prices in USD
- Only include factual information from your search"""

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 4096
                },
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"Perplexity API error: {e}")
            return f"Research failed: {str(e)}"
        except (KeyError, IndexError) as e:
            print(f"Perplexity response parsing error: {e}")
            return "Research failed: Unable to parse response"
