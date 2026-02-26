"""
Anthropic Claude API client wrapper.
"""
import os
import json
import streamlit as st

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def get_api_key():
    """Get API key from env, secrets, or session state."""
    # 1. Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    # 2. Streamlit secrets
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
        if key:
            return key
    except Exception:
        pass

    # 3. Session state (user input)
    return st.session_state.get("anthropic_api_key", "")


def is_ai_available():
    """Check if AI is available."""
    return HAS_ANTHROPIC and bool(get_api_key())


def render_api_key_input():
    """Render API key input in sidebar if not configured."""
    if not HAS_ANTHROPIC:
        st.sidebar.warning("Instale o pacote `anthropic`: pip install anthropic")
        return False

    if not get_api_key():
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Configurar IA**")
        key = st.sidebar.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            key="api_key_input",
        )
        if key:
            st.session_state["anthropic_api_key"] = key
            st.sidebar.success("API Key configurada!")
            return True
        st.sidebar.caption("Necessária para diagnósticos e recomendações com IA.")
        return False
    return True


def ask_claude(system_prompt, user_message, max_tokens=4096):
    """Send a message to Claude and get a response."""
    if not HAS_ANTHROPIC:
        return "[IA não disponível - instale: pip install anthropic]"

    api_key = get_api_key()
    if not api_key:
        return "[IA não configurada - insira sua API Key no sidebar]"

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception as e:
        return f"[Erro na IA: {str(e)}]"


def ask_claude_json(system_prompt, user_message, max_tokens=4096):
    """Send a message to Claude expecting JSON response."""
    enhanced_system = system_prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation."

    response = ask_claude(enhanced_system, user_message, max_tokens)

    # Try to extract JSON from response
    try:
        # Direct parse
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to find JSON block
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    return {"error": "Failed to parse AI response", "raw": response}
