import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from services.claude_service import ClaudeService, APIError
from services.prd_service import PRDService
from services.research_service import ResearchService
from config import SECRET_KEY, REDIS_URL, IS_PRODUCTION

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configure session storage
if REDIS_URL:
    # Production: Use Redis for session storage
    import redis
    app.config["SESSION_TYPE"] = "redis"
    app.config["SESSION_REDIS"] = redis.from_url(REDIS_URL)
    app.config["SESSION_PERMANENT"] = False
else:
    # Development: Use filesystem-based sessions
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = os.path.join(os.path.dirname(__file__), ".flask_session")
    app.config["SESSION_PERMANENT"] = False

Session(app)

claude_service = ClaudeService()
prd_service = PRDService()
research_service = ResearchService()

# Server-side conversation storage (avoids cookie size limits)
# Note: In production with multiple workers, consider using Redis for this too
conversations = {}


def get_session_id():
    """Get or create a session ID."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def get_messages():
    """Get messages for current session."""
    session_id = get_session_id()
    return conversations.get(session_id, [])


def set_messages(messages):
    """Set messages for current session."""
    session_id = get_session_id()
    conversations[session_id] = messages


@app.route("/")
def index():
    """Serve the main chat interface."""
    # Clear conversation on page load for fresh start
    set_messages([])
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle chat messages."""
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    # Get or initialize conversation history
    messages = get_messages()

    # Add user message to history
    messages.append({"role": "user", "content": user_message})

    try:
        # Get response from Claude
        assistant_response = claude_service.chat(messages)

        # Add assistant response to history
        messages.append({"role": "assistant", "content": assistant_response})

        # Save updated history
        set_messages(messages)

        return jsonify({
            "response": assistant_response,
            "message_count": len(messages)
        })

    except APIError as e:
        # Don't add failed message to history
        messages.pop()
        set_messages(messages)
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        messages.pop()
        set_messages(messages)
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/generate-prd", methods=["POST"])
def generate_prd():
    """Generate a PRD from the conversation."""
    messages = get_messages()

    if len(messages) < 2:
        return jsonify({"error": "Not enough conversation to generate a PRD"}), 400

    try:
        # Generate PRD content
        prd_content = claude_service.generate_prd(messages)

        # Save to file
        filename = prd_service.save_prd(prd_content)

        return jsonify({
            "prd": prd_content,
            "filename": filename
        })

    except APIError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/prds", methods=["GET"])
def list_prds():
    """List all saved PRDs."""
    prds = prd_service.list_prds()
    return jsonify({"prds": prds})


@app.route("/api/prds/<filename>", methods=["GET"])
def get_prd(filename):
    """Get a specific PRD by filename."""
    content = prd_service.get_prd(filename)
    if content:
        return jsonify({"content": content})
    return jsonify({"error": "PRD not found"}), 404


@app.route("/api/prds/<filename>/archive", methods=["POST"])
def archive_prd(filename):
    """Archive a PRD (with research) or research file by moving to old folder."""
    # If it's a PRD, use cascading archive to also archive associated research
    if "-prd-" in filename:
        result = prd_service.archive_prd_with_research(filename)
        if result["success"]:
            return jsonify({
                "success": True,
                "message": f"Archived {len(result['archived'])} file(s)",
                "archived": result["archived"]
            })
        return jsonify({"error": "Failed to archive PRD"}), 404
    else:
        # For research files, just archive the single file
        success = prd_service.archive_prd(filename)
        if success:
            return jsonify({"success": True, "message": f"Archived {filename}"})
        return jsonify({"error": "Failed to archive file"}), 404


@app.route("/api/clear", methods=["POST"])
def clear_conversation():
    """Clear the current conversation."""
    set_messages([])
    return jsonify({"success": True})


@app.route("/api/load-prd/<filename>", methods=["POST"])
def load_prd(filename):
    """Load an existing PRD for iteration."""
    content = prd_service.get_prd(filename)
    if not content:
        return jsonify({"error": "PRD not found"}), 404

    # Initialize conversation with the PRD as context
    messages = [
        {
            "role": "user",
            "content": f"I have an existing PRD that I'd like to iterate on and improve. Here it is:\n\n{content}"
        },
        {
            "role": "assistant",
            "content": "I've reviewed your existing PRD. I can help you iterate on and improve it. What changes or additions would you like to make? For example:\n\n- Add or modify features\n- Clarify requirements\n- Update technical considerations\n- Refine user stories\n- Add missing sections\n\nJust let me know what you'd like to focus on!"
        }
    ]
    set_messages(messages)

    return jsonify({
        "success": True,
        "content": content,
        "filename": filename,
        "message_count": len(messages)
    })


@app.route("/api/research", methods=["POST"])
def research():
    """Conduct web research on a topic and add findings to conversation."""
    data = request.get_json()
    research_type = data.get("type", "competitors")
    product_name = data.get("product_name", "")
    product_description = data.get("product_description", "")
    custom_query = data.get("query", "")

    try:
        if research_type == "competitors":
            if not product_name:
                return jsonify({"error": "Product name is required for competitor research"}), 400
            research_data = research_service.research_competitors(
                product_name,
                product_description or product_name
            )
            formatted_research = research_service.format_research_for_prompt(research_data)
        elif research_type == "custom":
            if not custom_query:
                return jsonify({"error": "Query is required for custom research"}), 400
            results = research_service.research_topic(custom_query, product_name)
            formatted_research = "## Research Results\n\n"
            for item in results:
                formatted_research += f"- **{item['title']}**\n"
                formatted_research += f"  {item['snippet']}\n"
                formatted_research += f"  Source: {item['link']}\n\n"
        else:
            return jsonify({"error": "Invalid research type"}), 400

        # Add research to conversation context
        messages = get_messages()
        research_message = f"I've conducted web research on the product/market. Here are the findings:\n\n{formatted_research}"

        messages.append({"role": "user", "content": research_message})

        # Get Claude to analyze the research
        analysis_prompt = """Based on this research, please provide:
1. A summary of the key competitors identified
2. Notable features and pricing patterns in the market
3. Gaps or opportunities you see for our product
4. Recommendations for differentiation

Keep your analysis concise but actionable."""

        try:
            analysis = claude_service.chat(messages + [{"role": "user", "content": analysis_prompt}])
            messages.append({"role": "assistant", "content": analysis})
            set_messages(messages)

            return jsonify({
                "research": formatted_research,
                "analysis": analysis,
                "message_count": len(messages)
            })
        except APIError as e:
            # Still return research even if analysis fails
            messages.append({"role": "assistant", "content": "I've received the research data. How would you like me to incorporate this into your PRD?"})
            set_messages(messages)
            return jsonify({
                "research": formatted_research,
                "analysis": "Research gathered successfully. API quota may be limited for detailed analysis.",
                "message_count": len(messages)
            })

    except Exception as e:
        return jsonify({"error": f"Research failed: {str(e)}"}), 500


@app.route("/api/research/search", methods=["POST"])
def research_search():
    """Simple web search endpoint."""
    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        results = research_service.search(query, max_results=10)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@app.route("/api/research/context", methods=["POST"])
def context_research():
    """Conduct context-aware research from conversation or existing PRD."""
    data = request.get_json()
    source = data.get("source", "conversation")

    try:
        # Extract product context based on source
        if source == "conversation":
            messages = get_messages()
            if not messages:
                return jsonify({
                    "error": "no_context",
                    "message": "No conversation found. Please describe your product idea or select an existing PRD."
                }), 400
            context = claude_service.extract_product_context(messages=messages)
        else:
            # Source is a PRD filename
            prd_content = prd_service.get_prd(source)
            if not prd_content:
                return jsonify({"error": "PRD not found"}), 404
            context = claude_service.extract_product_context(prd_content=prd_content)

        # Check if extraction was successful
        if not context.get("product_name") or context.get("confidence") == "none":
            return jsonify({
                "error": "insufficient_context",
                "message": "Could not identify a clear product from the source. Please provide more details about what you're building."
            }), 400

        # Run competitor research using Perplexity
        product_name = context["product_name"]
        product_description = context.get("product_description", product_name)
        # Use search_category for cleaner search queries (removes marketing words)
        search_term = context.get("search_category", product_name)

        # Perplexity returns the full analysis directly
        analysis = research_service.research_competitors(
            search_term,
            product_description
        )

        # Debug: log research results
        print(f"[DEBUG] Product: {product_name}, Search term: {search_term}")
        print(f"[DEBUG] Analysis length: {len(analysis)} chars")

        # Add research to conversation history so it's included in PRD generation
        messages = get_messages()
        messages.append({
            "role": "user",
            "content": f"I've gathered competitive research for {product_name}."
        })
        messages.append({
            "role": "assistant",
            "content": analysis
        })
        set_messages(messages)

        return jsonify({
            "success": True,
            "product_name": product_name,
            "product_description": product_description,
            "source": source,
            "analysis": analysis,
            "confidence": context.get("confidence", "medium"),
            "debug": {
                "search_term": search_term,
                "analysis_length": len(analysis)
            }
        })

    except Exception as e:
        return jsonify({"error": f"Research failed: {str(e)}"}), 500


@app.route("/api/research/save", methods=["POST"])
def save_research():
    """Save competitive analysis to PRD or as separate file."""
    data = request.get_json()
    content = data.get("content", "")
    save_type = data.get("save_type", "separate_file")
    prd_filename = data.get("prd_filename", "")
    product_name = data.get("product_name", "Product")

    if not content:
        return jsonify({"error": "No content to save"}), 400

    try:
        if save_type == "append_prd":
            if not prd_filename:
                return jsonify({"error": "PRD filename required for append"}), 400

            # Format as competitive analysis section
            section_content = "## Competitive Analysis\n\n" + content

            success = prd_service.append_to_prd(prd_filename, section_content)
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Competitive analysis added to {prd_filename}",
                    "filename": prd_filename
                })
            else:
                return jsonify({"error": "Failed to append to PRD"}), 500
        else:
            # Save as separate file
            filename = prd_service.save_research(content, product_name)
            return jsonify({
                "success": True,
                "message": f"Competitive analysis saved as {filename}",
                "filename": filename
            })

    except Exception as e:
        return jsonify({"error": f"Save failed: {str(e)}"}), 500


@app.route("/health")
def health():
    """Health check endpoint for Railway/container orchestration."""
    return jsonify({
        "status": "healthy",
        "service": "prdy"
    })


if __name__ == "__main__":
    # Local development only - production uses gunicorn via Procfile
    app.run(debug=True, port=5001, host="127.0.0.1")
