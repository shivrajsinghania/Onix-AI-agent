TOOLS = {

    "send_message": {
    
        "description":
            "Send message to someone",
            
        "apps": [
        "whatsapp",
        "instagram",
        "messenger"
        ],

        "required_fields": [
            "target",
            "message"
        ]
    },

    "search": {

        "description":
            "Search something online",

        "apps": [
            "google",
            "youtube"
        ],

        "required_fields": [
            "query"
        ]
    },
    
    "observe_website": {

    "description":
        "Read and analyze website content",

    "apps": [
        "browser"
    ],

    "required_fields": [
        "url"
    ]
    },
    
    "open_website": {

    "description":
        "Open a website",

    "apps": [
        "browser"
    ],

    "required_fields": [
        "url"
    ]
    },
    
    "click_element": {

    "description":
        "Click an element",

    "apps": [
        "browser"
    ],

    "required_fields": [
        "element"
    ]
    },
    
    "type_text": {

    "description":
        "Type text into input",

    "apps": [
        "browser"
    ],

    "required_fields": [
        "text"
    ]
    },
    
    "submit_form": {

    "description":
        "Submit form",

    "apps": [
        "browser"
    ],

    "required_fields": []
    }
}
