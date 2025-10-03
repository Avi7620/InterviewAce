import google.generativeai as genai

# Directly use your API key
genai.configure(api_key="AIzaSyBDEBVHTiEOT-D-exTbbEDuZD1swWQwvio")

# Choose a supported model
model = genai.GenerativeModel("gemini-2.5-flash")

# Generate content
response = model.generate_content("Give me 3 interview questions about Flask.")
print(response.text)
