import requests
from bs4 import BeautifulSoup

def observe_website(url):
	response = requests.get(url)
	soup = BeautifulSoup(response.text, "html.parser")
	title = "No title found"
	
	if soup.title:
		title = soup.title.string
		
	return {"title": title}
