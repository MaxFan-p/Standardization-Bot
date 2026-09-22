from google import genai

client = genai.Client(vertexai=True)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Write three random sentences",
)
print(response.text)