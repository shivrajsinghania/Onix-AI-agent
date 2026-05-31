from tools.reasoner import analyze_ai

def analyze_observation(observation):
	
	prompt = f"""
	Analyze this observation.
	
	Observation: {observation}
	
	Give a short summary.	
	"""
	return analyze_ai(prompt)