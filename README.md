# PRDy

An AI-powered Product Requirements Document generator. Have a conversation about your product idea and generate a comprehensive PRD with competitive research.

## Features

- **Conversational PRD Creation** - Describe your product idea in natural language, answer clarifying questions, and generate a structured PRD
- **Competitive Research** - Integrated Perplexity AI search to analyze competitors, pricing, and market positioning
- **Document Management** - Save, load, and iterate on PRDs with a sidebar interface
- **Hierarchical Organization** - Research files are nested under their parent PRDs
- **Archive System** - Archive old PRDs (moves to `output/old/` rather than deleting)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/OmniJeff/prdy.git
   cd prdy
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add:
   - `ANTHROPIC_API_KEY` - Get from [Anthropic Console](https://console.anthropic.com/)
   - `PERPLEXITY_API_KEY` - Get from [Perplexity](https://www.perplexity.ai/settings/api)

4. Run the app:
   ```bash
   python3 app.py
   ```

5. Open http://127.0.0.1:5001 in your browser

## Usage

1. **Start a conversation** - Describe your product idea in the chat
2. **Answer questions** - The AI will ask clarifying questions about features, users, scope
3. **Run research** - Click "Research" to gather competitive intelligence
4. **Generate PRD** - Click "Generate PRD" when ready
5. **Iterate** - Load saved PRDs from the sidebar to refine them

## Project Structure

```
prdy/
├── app.py                 # Flask application and routes
├── config.py              # Configuration and environment variables
├── services/
│   ├── claude_service.py  # Claude API integration
│   ├── prd_service.py     # PRD file management
│   └── research_service.py # Perplexity API integration
├── prompts/
│   └── system_prompts.py  # AI system prompts
├── static/
│   ├── css/style.css      # Styling
│   └── js/chat.js         # Frontend logic
├── templates/
│   └── index.html         # Main page template
├── output/                # Generated PRDs (gitignored)
└── tests/                 # Test suite
```

## License

MIT
