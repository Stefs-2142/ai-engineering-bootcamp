import streamlit as st
import requests
from chatbot_ui.core.config import config


st.set_page_config(
    page_title="Amazon Product Assistant",
    page_icon="🛒",
    layout="centered"
)

st.title("Amazon Product Assistant")
st.caption("Hybrid RAG + SQL Agent - Ask about products, prices, ratings, and more!")


def api_call(method, url, **kwargs):

    def _show_error_popup(message):
        """Show error message as a popup in the top-right corner."""
        st.session_state["error_popup"] = {
            "visible": True,
            "message": message,
        }

    try:
        response = getattr(requests, method)(url, **kwargs)

        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            response_data = {"message": "Invalid response format from server"}

        if response.ok:
            return True, response_data

        return False, response_data

    except requests.exceptions.ConnectionError:
        _show_error_popup("Connection error. Please check your network connection.")
        return False, {"message": "Connection error"}
    except requests.exceptions.Timeout:
        _show_error_popup("The request timed out. Please try again later.")
        return False, {"message": "Request timeout"}
    except Exception as e:
        _show_error_popup(f"An unexpected error occurred: {str(e)}")
        return False, {"message": str(e)}


# Intent badge styling
INTENT_BADGES = {
    "rag": ("Semantic Search", "blue"),
    "sql": ("SQL Query", "green"),
    "hybrid": ("Hybrid Filter+Search", "orange")
}


if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I'm your Amazon Product Assistant. I can help you:\n\n"
                       "- **Find products** by description (\"wireless earbuds for running\")\n"
                       "- **Query data** with filters (\"how many products cost over $100\")\n"
                       "- **Hybrid search** (\"best headphones under $50 with good bass\")\n\n"
                       "What are you looking for today?",
            "intent": None
        }
    ]


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Show intent badge for assistant messages
        if message["role"] == "assistant" and message.get("intent"):
            intent = message["intent"]
            label, color = INTENT_BADGES.get(intent, (intent, "gray"))
            st.caption(f":{color}[{label}]")
        st.markdown(message["content"])


if prompt := st.chat_input("Ask about products, prices, ratings..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Use smart /chat endpoint
            success, response_data = api_call(
                "post",
                f"{config.API_URL}/chat",
                json={"query": prompt}
            )

            if success:
                answer = response_data.get("answer", "No response")
                intent = response_data.get("intent", "rag")

                # Show intent badge
                label, color = INTENT_BADGES.get(intent, (intent, "gray"))
                st.caption(f":{color}[{label}]")

                # Show filters if present
                filters = response_data.get("filters")
                if filters and any(v is not None for v in filters.values()):
                    filter_parts = []
                    if filters.get("min_price"):
                        filter_parts.append(f"min ${filters['min_price']}")
                    if filters.get("max_price"):
                        filter_parts.append(f"max ${filters['max_price']}")
                    if filters.get("min_rating"):
                        filter_parts.append(f"rating {filters['min_rating']}+")
                    if filters.get("category"):
                        filter_parts.append(f"category: {filters['category']}")
                    if filter_parts:
                        st.caption(f"Filters: {', '.join(filter_parts)}")

                st.markdown(answer)
            else:
                answer = f"Error: {response_data.get('message', 'Unknown error')}"
                intent = None
                st.error(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "intent": intent
    })