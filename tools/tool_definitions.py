TOOLS = {

    "research_service": {
        "description": "Research how to apply for a government service in a specific state",
        "apps": ["browser"],
        "required_fields": ["service", "state"]
    },

    "search": {
        "description": "Search something online",
        "apps": ["google", "youtube"],
        "required_fields": ["query"]
    },

    "observe_website": {
        "description": "Read and analyze website content",
        "apps": ["browser"],
        "required_fields": ["url"]
    },

    "open_website": {
        "description": "Open a website",
        "apps": ["browser"],
        "required_fields": ["url"]
    },

    "click_element": {
        "description": "Click an element on a webpage",
        "apps": ["browser"],
        "required_fields": ["element"]
    },

    "type_text": {
        "description": "Type text into an input field",
        "apps": ["browser"],
        "required_fields": ["text"]
    },

    "submit_form": {
        "description": "Submit a form",
        "apps": ["browser"],
        "required_fields": []
    }
}