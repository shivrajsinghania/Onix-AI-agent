import webbrowser

def search(app, query):
    if app == "youtube":

        url = (
            "https://www.youtube.com/results?"
            f"search_query={query}"
        )

        webbrowser.open(url)

        print(f"Searching YouTube for: {query}")

    elif app == "google":

        url = (
            f"https://www.google.com/search?q={query}"
        )

        webbrowser.open(url)

        print(f"Searching Google for: {query}")
